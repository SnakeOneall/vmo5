import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime

# Conectar ao MetaTrader 5
if not mt5.initialize(login=412278, password="J0@0h3nr1qu3", server="MetaQuotes-Demo"):
    print("Erro ao conectar:", mt5.last_error())
    quit()

# Selecionar o símbolo do Mini Dólar
simbolo = "WDOH25"  # Ajuste para o contrato atual (ex.: WDOJ25 para abril de 2025)
if not mt5.symbol_select(simbolo, True):
    print(f"Erro ao selecionar {simbolo}:", mt5.last_error())
    mt5.shutdown()
    quit()

# Coletar dados por 60 segundos
print(f"Coletando dados em tempo real de {simbolo} por 60 segundos...")
dados = []
inicio = time.time()
while time.time() - inicio < 60:  # Coleta por 1 minuto
    tick = mt5.symbol_info_tick(simbolo)
    if tick:
        dados.append({
            'timestamp': datetime.fromtimestamp(tick.time),
            'bid': tick.bid,
            'ask': tick.ask,
            'volume': tick.volume
        })
    time.sleep(0.5)  # Atualiza a cada 0,5 segundos

# Desconectar
mt5.shutdown()

# Converter para DataFrame
df = pd.DataFrame(dados)
df['close'] = (df['bid'] + df['ask']) / 2  # Média entre bid e ask como "close"
print(f"Dados coletados: {len(df)} ticks")
print(df.head())  # Mostra as primeiras linhas

# Salvar em CSV para usar depois
df.to_csv("C:/Users/Andre Santos/Downloads/dados_wdo.csv", index=False)
print("Dados salvos em 'dados_wdo.csv'")