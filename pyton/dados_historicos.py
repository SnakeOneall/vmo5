import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

# Conectar ao MetaTrader 5
if not mt5.initialize(login=412278, password="J0@0h3nr1qu3", server="GenialInvestimentos-PRD"):
    print("Erro ao conectar:", mt5.last_error())
    quit()

# Selecionar o símbolo
simbolo = "WDOH25"  # Ajuste para o contrato atual (ex.: WDOJ25 para abril)
if not mt5.symbol_select(simbolo, True):
    print(f"Erro ao selecionar {simbolo}:", mt5.last_error())
    mt5.shutdown()
    quit()

# Definir período (últimos 30 dias, antes do feriado)
data_fim = datetime(2025, 2, 28)  # Antes do feriado de Carnaval
data_inicio = data_fim - timedelta(days=30)

# Baixar dados históricos (timeframe de 5 minutos)
rates = mt5.copy_rates_range(simbolo, mt5.TIMEFRAME_M5, data_inicio.timestamp(), data_fim.timestamp())

# Converter para DataFrame
if rates is not None and len(rates) > 0:
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df.rename(columns={
        'time': 'timestamp',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'tick_volume': 'volume',
        'spread': 'spread',
        'real_volume': 'real_volume'
    })
    print(f"Dados históricos coletados: {len(df)} candles")
    print(df.head())
    # Salvar em CSV
    df.to_csv("C:/Users/Andre Santos/Downloads/dados_wdo_historicos.csv", index=False)
    print("Dados salvos em 'dados_wdo_historicos.csv'")
else:
    print("Nenhum dado histórico encontrado:", mt5.last_error())

# Desconectar
mt5.shutdown()