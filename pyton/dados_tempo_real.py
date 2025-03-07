import MetaTrader5 as mt5
import time

# Conectar ao MT5
if not mt5.initialize(login=412278, password="J0@0h3nr1qu3", server="GenialInvestimentos-PRD"):
    print("Erro ao conectar:", mt5.last_error())
    quit()

# Selecionar o símbolo (Mini Dólar)
simbolo = "WDOH25"  # WDO para março de 2025, ajuste conforme o contrato atual
if not mt5.symbol_select(simbolo, True):
    print(f"Erro ao selecionar {simbolo}:", mt5.last_error())
    mt5.shutdown()
    quit()

# Loop para pegar dados em tempo real
print(f"Extraindo dados em tempo real de {simbolo}...")
for _ in range(10):  # Executa 10 vezes, para testar
    tick = mt5.symbol_info_tick(simbolo)
    if tick is not None:
        print(f"Hora: {tick.time}, Bid: {tick.bid}, Ask: {tick.ask}")
    else:
        print("Erro ao obter tick:", mt5.last_error())
    time.sleep(1)  # Espera 1 segundo entre cada atualização

# Desconectar
mt5.shutdown()