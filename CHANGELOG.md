# Registro de Alterações (Changelog) - NfSplit

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.
O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/), e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.0.0] - 2026-11-21

### ✨ Lançamento Oficial da Versão 1.0

#### Adicionado
* **Executável Desktop Autônomo (`.exe`)**:
  * Distribuição em binário único portátil para Windows (`NfSplit.exe`), sem necessidade de instalação de Python ou dependências externas.
  * Execução 100% offline, local e segura, sem necessidade de servidores locais ou portas abertas.
* **Interface Moderna e Suavizada com CustomTkinter**:
  * Design visual moderno com cantos arredondados verdadeiros em cartões (`corner_radius=16`), botões com animações suaves e campos de texto arredondados.
  * Ícone personalizado e suporte a temas visuais de alto contraste e ergonomia.
* **Caixas de Diálogo e Confirmação 100% Nativas do Sistema**:
  * Substituição de todas as caixas de mensagem padrão do Windows (Win32) por modais gráficos integrados ao visual do aplicativo (Sucesso, Atenção, Erro e Confirmações).
* **Gestão Inteligente de Pasta de Saída**:
  * Caminho de salvamento limpo por padrão na primeira inicialização.
  * Solicitação amigável na primeira execução com gravação persistente das preferências em `config.json`.
* **Motor de Extração e Classificação Preciso**:
  * Extração direta da Chave de Acesso de 44 dígitos (`chave[25:34]` para o número exato da DANFE).
  * Rastreamento e junção automática de DANFEs com múltiplas páginas contínuas.
  * Leitor universal de boletos FEBRABAN com identificação precisa de valor (centavos), banco emissor, vencimento e parcela.
  * Preservação integral e lossless (sem compressão e sem alteração dos códigos de barras) dos documentos originais.
* **Opções de Organização**:
  * Junção opcional de DANFE + Boleto em arquivo PDF único.
  * Separação de Mapas de Entrega e Acertos de Carga em arquivos dedicados.
  * Limpeza automática de prefixos de CNPJ da Razão Social nos nomes dos arquivos gerados.
* **Relatório em Planilha Excel/CSV**:
  * Geração automática de `relatorio.csv` com codificação UTF-8 com BOM, delimitado por ponto e vírgula, contendo valores, vencimentos, forma de pagamento e chave de acesso.
* **Arquitetura de Atualização OTA (Over-The-Air)**:
  * Módulo [updater.py] integrado para futuras atualizações automáticas via servidor ou repositório, com verificação de SHA-256 e substituição atômica de executável.
