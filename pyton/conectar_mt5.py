import MetaTrader5 as mt5

# Conectar ao MetaTrader 5
if not mt5.initialize(login=412278, password="J0@0h3nr1qu3", server="GenialInvestimentos-PRD"):
    print("Erro ao conectar:", mt5.last_error())
    quit()

# Verificar a conexão
print("Conectado ao MetaTrader 5!")
print("Informações do terminal:", mt5.terminal_info())

# Desconectar
mt5.shutdown()