import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import time

class MiniDolarStrategy:
    def __init__(self, periodo_curto=9, periodo_medio=21, periodo_longo=50, 
                 rsi_periodo=14, rsi_sobrevenda=30, rsi_sobrecompra=70,
                 atr_periodo=14, atr_multiplicador=2):
        """
        Inicializa a estratégia com os parâmetros definidos
        """
        self.periodo_curto = periodo_curto
        self.periodo_medio = periodo_medio
        self.periodo_longo = periodo_longo
        self.rsi_periodo = rsi_periodo
        self.rsi_sobrevenda = rsi_sobrevenda
        self.rsi_sobrecompra = rsi_sobrecompra
        self.atr_periodo = atr_periodo
        self.atr_multiplicador = atr_multiplicador
        
    def calcular_medias_moveis(self, df):
        """Calcula as médias móveis exponenciais"""
        df['MM_Curta'] = df['close'].ewm(span=self.periodo_curto, adjust=False).mean()
        df['MM_Media'] = df['close'].ewm(span=self.periodo_medio, adjust=False).mean()
        df['MM_Longa'] = df['close'].ewm(span=self.periodo_longo, adjust=False).mean()
        return df
    
    def calcular_rsi(self, df):
        """Calcula o RSI (Índice de Força Relativa)"""
        delta = df['close'].diff()
        ganhos = delta.copy()
        perdas = delta.copy()
        ganhos[ganhos < 0] = 0
        perdas[perdas > 0] = 0
        perdas = abs(perdas)
        
        media_ganhos = ganhos.rolling(window=self.rsi_periodo).mean()
        media_perdas = perdas.rolling(window=self.rsi_periodo).mean()
        
        rs = media_ganhos / media_perdas
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    
    def calcular_atr(self, df):
        """Calcula o ATR (Average True Range)"""
        df['tr1'] = abs(df['high'] - df['low'])
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['TR'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=self.atr_periodo).mean()
        return df
    
    def identificar_suporte_resistencia(self, df):
        """Identifica níveis de suporte e resistência usando pivôs"""
        # Identificação de pivôs de alta (resistência)
        df['pivo_alta'] = df['high'].rolling(window=5, center=True).apply(
            lambda x: 1 if x[2] == max(x) else 0, raw=True
        )
        
        # Identificação de pivôs de baixa (suporte)
        df['pivo_baixa'] = df['low'].rolling(window=5, center=True).apply(
            lambda x: 1 if x[2] == min(x) else 0, raw=True
        )
        
        # Preços dos pivôs
        df['nivel_resistencia'] = np.where(df['pivo_alta'] == 1, df['high'], np.nan)
        df['nivel_suporte'] = np.where(df['pivo_baixa'] == 1, df['low'], np.nan)
        
        # Preenche valores NaN com o último valor válido usando ffill
        df['nivel_resistencia'] = df['nivel_resistencia'].ffill()
        df['nivel_suporte'] = df['nivel_suporte'].ffill()
        
        return df
    
    def calcular_volume_profile(self, df):
        """Calcula o perfil de volume para identificar áreas de interesse"""
        # Remover valores NaN ou infinitos
        df = df.dropna(subset=['close', 'volume'])
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        
        # Divide o range de preços em 10 faixas
        price_min = df['low'].min()
        price_max = df['high'].max()
        if price_max == price_min:  # Evitar divisão por zero
            price_max += 0.01
        price_delta = (price_max - price_min) / 10
        
        df['price_zone'] = ((df['close'] - price_min) / price_delta).astype(int).clip(0, 9)
        volume_profile = df.groupby('price_zone')['volume'].sum()
        
        # Identifica zona de maior volume (Point of Control - POC)
        if not volume_profile.empty:
            poc_zone = volume_profile.idxmax()
            poc_price = price_min + (poc_zone + 0.5) * price_delta
        else:
            poc_price = df['close'].mean()  # Valor padrão se não houver dados
        
        df['poc_price'] = poc_price
        return df
    
    def verificar_correlacao_dolar(self, data_atual):
        """
        Simula uma verificação de correlação com mercado de USD global
        """
        dia_semana = data_atual.weekday()
        correlacoes = {
            0: 0.65,  # Segunda
            1: 0.70,  # Terça
            2: 0.75,  # Quarta
            3: 0.68,  # Quinta
            4: 0.60,  # Sexta
            5: 0.40,  # Sábado (mercado fechado, valor baixo)
            6: 0.40,  # Domingo (mercado fechado, valor baixo)
        }
        return correlacoes.get(dia_semana, 0.5)
    
    def verificar_horarios_otimos(self, hora_atual):
        """Verifica se o horário atual é ótimo para operações no mini dólar"""
        if 9 <= hora_atual < 10:  # Abertura do mercado - alta volatilidade
            return 0.9
        elif 10 <= hora_atual < 12:  # Mercado em consolidação
            return 0.7
        elif 12 <= hora_atual < 13:  # Horário de almoço - baixa liquidez
            return 0.3
        elif 13 <= hora_atual < 15:  # Abertura mercado americano - alta volatilidade
            return 0.9
        elif 15 <= hora_atual < 17:  # Alta liquidez
            return 0.8
        elif 17 <= hora_atual < 18:  # Fechamento - alta volatilidade
            return 0.7
        else:
            return 0.2  # Fora do horário comercial
    
    def gerar_sinais(self, df):
        """Gera sinais de compra e venda com base nos indicadores calculados"""
        df = self.calcular_medias_moveis(df)
        df = self.calcular_rsi(df)
        df = self.calcular_atr(df)
        df = self.identificar_suporte_resistencia(df)
        df = self.calcular_volume_profile(df)
        
        df['sinal'] = 0
        df['forca_sinal'] = 0.0
        df['stop_loss'] = np.nan
        df['alvo_lucro'] = np.nan
        
        df['timestamp'] = [datetime(2025, 3, 3, 9, 0) + timedelta(minutes=5*i) for i in range(len(df))]
        
        for i in range(2, len(df)):
            cruzamento_alta = df['MM_Curta'].iloc[i-1] <= df['MM_Media'].iloc[i-1] and df['MM_Curta'].iloc[i] > df['MM_Media'].iloc[i]
            cruzamento_baixa = df['MM_Curta'].iloc[i-1] >= df['MM_Media'].iloc[i-1] and df['MM_Curta'].iloc[i] < df['MM_Media'].iloc[i]
            rsi_sobrevenda = df['RSI'].iloc[i] < self.rsi_sobrevenda
            rsi_sobrecompra = df['RSI'].iloc[i] > self.rsi_sobrecompra
            tendencia_alta = df['close'].iloc[i] > df['MM_Longa'].iloc[i]
            tendencia_baixa = df['close'].iloc[i] < df['MM_Longa'].iloc[i]
            proximo_suporte = abs(df['close'].iloc[i] - df['nivel_suporte'].iloc[i]) < df['ATR'].iloc[i] * 0.5
            proximo_resistencia = abs(df['close'].iloc[i] - df['nivel_resistencia'].iloc[i]) < df['ATR'].iloc[i] * 0.5
            volume_aumentando = df['volume'].iloc[i] > df['volume'].iloc[i-1]
            confirmacao_alta = df['close'].iloc[i] > df['open'].iloc[i]
            confirmacao_baixa = df['close'].iloc[i] < df['open'].iloc[i]
            
            hora_atual = df['timestamp'].iloc[i].hour
            fator_horario = self.verificar_horarios_otimos(hora_atual)
            correlacao_global = self.verificar_correlacao_dolar(df['timestamp'].iloc[i])
            
            if cruzamento_alta and tendencia_alta and volume_aumentando and confirmacao_alta:
                df['sinal'].iloc[i] = 1
                forca_base = 0.6
                if rsi_sobrevenda: forca_base += 0.2
                if proximo_suporte: forca_base += 0.1
                df['forca_sinal'].iloc[i] = min(forca_base * fator_horario * correlacao_global, 1.0)
                preco = df['close'].iloc[i]
                df['stop_loss'].iloc[i] = preco - df['ATR'].iloc[i] * self.atr_multiplicador
                df['alvo_lucro'].iloc[i] = preco + df['ATR'].iloc[i] * self.atr_multiplicador * 2
            
            elif cruzamento_baixa and tendencia_baixa and volume_aumentando and confirmacao_baixa:
                df['sinal'].iloc[i] = -1
                forca_base = 0.6
                if rsi_sobrecompra: forca_base += 0.2
                if proximo_resistencia: forca_base += 0.1
                df['forca_sinal'].iloc[i] = min(forca_base * fator_horario * correlacao_global, 1.0)
                preco = df['close'].iloc[i]
                df['stop_loss'].iloc[i] = preco + df['ATR'].iloc[i] * self.atr_multiplicador
                df['alvo_lucro'].iloc[i] = preco - df['ATR'].iloc[i] * self.atr_multiplicador * 2
        
        return df

    def filtrar_melhores_sinais(self, df, forca_minima=0.7):
        """Filtra apenas os sinais com força acima do limiar definido"""
        return df[(df['sinal'] != 0) & (df['forca_sinal'] >= forca_minima)]
    
    def backtest(self, df, capital_inicial=10000, lotes=1, risco_por_operacao=0.01):
        """
        Executa um backtest simples da estratégia
        """
        df_sinais = self.filtrar_melhores_sinais(df, forca_minima=0.8)
        valor_ponto = 10
        capital_atual = capital_inicial
        operacoes = []
        
        for i in range(len(df_sinais)):
            if capital_atual <= 0:
                break
            
            tipo_operacao = 'compra' if df_sinais['sinal'].iloc[i] == 1 else 'venda'
            entrada = df_sinais['close'].iloc[i]
            stop = df_sinais['stop_loss'].iloc[i]
            alvo = df_sinais['alvo_lucro'].iloc[i]
            
            risco_monetario = capital_atual * risco_por_operacao
            pontos_risco = abs(entrada - stop)
            lotes_ajustados = min(lotes, risco_monetario / (pontos_risco * valor_ponto))
            
            idx_original = df.index.get_loc(df_sinais.index[i])
            for j in range(idx_original + 1, min(idx_original + 20 + 1, len(df))):
                preco_high = df['high'].iloc[j]
                preco_low = df['low'].iloc[j]
                preco_close = df['close'].iloc[j]
                
                if tipo_operacao == 'compra':
                    if preco_low <= stop:
                        resultado_pts = stop - entrada
                        break
                    elif preco_high >= alvo:
                        resultado_pts = alvo - entrada
                        break
                    elif j == idx_original + 20:
                        resultado_pts = preco_close - entrada
                        break
                else:
                    if preco_high >= stop:
                        resultado_pts = entrada - stop
                        break
                    elif preco_low <= alvo:
                        resultado_pts = entrada - alvo
                        break
                    elif j == idx_original + 20:
                        resultado_pts = preco_close - entrada
                        break
            
            resultado_financeiro = resultado_pts * valor_ponto * lotes_ajustados
            capital_atual += resultado_financeiro
            
            operacoes.append({
                'data': df_sinais['timestamp'].iloc[i],
                'tipo': tipo_operacao,
                'entrada': entrada,
                'saida': entrada + resultado_pts,
                'resultado_financeiro': resultado_financeiro,
                'capital_apos_operacao': capital_atual
            })
        
        df_resultados = pd.DataFrame(operacoes)
        if len(df_resultados) > 0:
            df_resultados['resultado_acumulado'] = df_resultados['resultado_financeiro'].cumsum()
            total_operacoes = len(df_resultados)
            taxa_acerto = sum(df_resultados['resultado_financeiro'] > 0) / total_operacoes * 100 if total_operacoes > 0 else 0
            max_drawdown = (df_resultados['capital_apos_operacao'].cummax() - df_resultados['capital_apos_operacao']).max() if not df_resultados.empty else 0
            
            metricas = {
                'capital_final': capital_atual,
                'taxa_acerto': taxa_acerto,
                'max_drawdown': max_drawdown,
                'retorno_percentual': (capital_atual - capital_inicial) / capital_inicial * 100 if capital_inicial > 0 else 0
            }
            return df_resultados, metricas
        return pd.DataFrame(), {}
    
    def obter_dados_tempo_real(self, simbolo="WDOH25", duracao_segundos=300):
        """Obtém dados em tempo real do MT5."""
        if not mt5.initialize():
            print("Erro ao conectar ao MT5:", mt5.last_error())
            return None

        if not mt5.symbol_select(simbolo, True):
            print(f"Erro ao selecionar {simbolo}:", mt5.last_error())
            mt5.shutdown()
            return None

        dados = []
        inicio = time.time()
        print(f"Coletando dados de {simbolo} por {duracao_segundos} segundos...")
        while time.time() - inicio < duracao_segundos:
            tick = mt5.symbol_info_tick(simbolo)
            if tick:
                dados.append({
                    'timestamp': datetime.fromtimestamp(tick.time),
                    'open': tick.last if tick.last else (tick.bid + tick.ask) / 2,
                    'high': tick.last if tick.last else (tick.bid + tick.ask) / 2,
                    'low': tick.last if tick.last else (tick.bid + tick.ask) / 2,
                    'close': (tick.bid + tick.ask) / 2,
                    'volume': tick.volume
                })
            time.sleep(0.5)

        mt5.shutdown()
        return pd.DataFrame(dados)
    
    def demo(self):
        print("=== Estratégia Automática para Mini Dólar (WDO) ===")
        try:
            dados_historicos = pd.read_csv("C:/Users/Andre Santos/Downloads/dados_wdo_historicos.csv")
            dados_historicos['timestamp'] = pd.to_datetime(dados_historicos['timestamp'])
            print(f"Dados históricos carregados: {len(dados_historicos)} candles")
        except FileNotFoundError:
            print("Erro: Arquivo 'dados_wdo_historicos.csv' não encontrado. Tentando coletar dados em tempo real...")
            dados_reais = self.obter_dados_tempo_real(simbolo="WDOH25", duracao_segundos=300)
            if dados_reais is not None and not dados_reais.empty:
                print(f"Dados em tempo real carregados: {len(dados_reais)} ticks")
                dados_com_sinais = self.gerar_sinais(dados_reais)
            else:
                print("Erro ao obter dados reais. Verifique o mercado ou conexão com MT5.")
                return
        else:
            dados_com_sinais = self.gerar_sinais(dados_historicos)
        
        melhores_sinais = self.filtrar_melhores_sinais(dados_com_sinais, forca_minima=0.7)
        print(f"Sinais de compra: {len(melhores_sinais[melhores_sinais['sinal'] == 1])}")
        print(f"Sinais de venda: {len(melhores_sinais[melhores_sinais['sinal'] == -1])}")
        resultados, metricas = self.backtest(dados_com_sinais)
        if metricas:
            print(f"Taxa de acerto: {metricas['taxa_acerto']:.2f}%")
            print(f"Drawdown máximo: R$ {metricas['max_drawdown']:.2f}")
            print(f"Retorno: {metricas['retorno_percentual']:.2f}%")

if __name__ == "__main__":
    estrategia = MiniDolarStrategy()
    estrategia.demo()