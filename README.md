# redes2526_projeto_multiplayergame

## Funcionalidades Principais
* **Arquitetura P2P:** Cada jogador atua simultaneamente como cliente (para enviar ações) e servidor (para receber ações de outros).
* **Comunicação gRPC:** As ações do jogo (atacar, mover, falar) são enviadas através de chamadas gRPC, utilizando ficheiros `.proto` para serialização.
* **Descoberta de Nós (DHT):** Os endereços IP e Portas dos jogadores são registados e consultados numa *Distributed Hash Table* para permitir que os nós se encontrem na rede.
* **Interface Assíncrona:** O terminal aceita comandos continuamente sem bloquear, utilizando `aioconsole` e `asyncio` para gerir o input do utilizador e a receção de eventos de rede em *background*.