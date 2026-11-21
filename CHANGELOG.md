# Registro de Alterações (Changelog) - NfSplit

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.
O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/), e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.1.0] - 2026-11-21

### 🚀 Atualização de Funcionalidades & Identidade Visual

#### Adicionado
* **Identificação Oficial com Versão no Nome**:
  * Título da janela principal atualizado para exibir explicitamente o nome e a versão: `NfSplit v1.1.0 • Separador de Notas & Boletos`.
  * Cabeçalho e telas de diálogo com carimbo visual permanente da versão ativa (`NfSplit v1.1.0`).
* **Sistema de Atualizações Automáticas OTA via GitHub Releases**:
  * Integração nativa à API oficial do repositório [`LivertonAguiar/NfSplit`](https://github.com/LivertonAguiar/NfSplit).
  * Rotina silenciosa de verificação automática semanal e botão de consulta manual imediata em "Sobre & OTA".
  * Caixa de diálogo de aprovação (`DialogoNovaVersao`) exibindo comparativo de versões, notas de atualização e tamanho do download.
  * Modal com barra de progresso em tempo real (`DialogoProgressoDownload`) exibindo velocidade, MBs baixados e porcentagem.
  * Substituição atômica automática do executável via processo em lote desanexado, com reinício instantâneo na nova versão e preservação 100% de `config.json`.
* **Redesign da Tabela de Resultados**:
  * Substituição da árvore clássica legada por `CTkScrollableFrame` nativo com barras de rolagem arredondadas e suaves.
  * Estado vazio ilustrado (*Empty State*) amigável e explicativo (`📄✨`).
  * Linhas em cartões com badges coloridos por tipo (`[DANFE]`, `[BOLETO]`, `[MAPA]`, `[ACERTO]`), efeito hover e botão direto "Abrir ↗".
* **Interatividade com Arraste e Solte & Explorer**:
  * Suporte nativo a Arraste e Solte (*Drag & Drop*) de PDFs diretamente sobre a janela.
  * Abertura do Windows Explorer ao clicar diretamente nas caixas de texto de entrada e saída.

---

## [1.0.0] - 2026-11-21

### ✨ Lançamento Oficial da Versão 1.0

#### Adicionado
* **Executável Desktop Autônomo (`.exe`)**:
  * Distribuição em binário único portátil para Windows (`NfSplit.exe`), sem necessidade de instalação de Python ou dependências externas.
  * Execução 100% offline, local e segura, sem necessidade de servidores locais ou portas abertas.
* **Interface Moderna e Suavizada com CustomTkinter**:
  * Design visual moderno com cantos arredondados verdadeiros em cartões (`corner_radius=16`), botões com animações suaves e campos de texto arredondados.
  * Tabela de resultados totalmente modernizada com `CTkScrollableFrame`, eliminando barras de rolagem legadas e exibindo scrollbars arredondadas e suaves.
  * Estado vazio ilustrado (*Empty State*) amigável e explicativo (`📄✨`) quando nenhum documento foi processado.
  * Badges coloridos por tipo de documento (`[DANFE]`, `[BOLETO]`, `[MAPA]`, `[ACERTO]`), efeito hover e botão de ação direta para abrir cada PDF gerado.
  * Suporte nativo a Arraste e Solte (*Drag & Drop*) de PDFs e pastas diretamente sobre a aplicação com feedback visual interativo.
  * Interatividade aprimorada com abertura do explorador ao clicar diretamente nas caixas de texto.
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
* **Sistema Completo de Atualização de Software (GitHub Releases OTA)**:
  * Integração direta com a API oficial do GitHub Releases (`LivertonAguiar/NfSplit`).
  * Verificação automática semanal em segundo plano e busca manual a qualquer momento em "Sobre & OTA".
  * Caixa de diálogo moderna (`DialogoNovaVersao`) exibindo comparativo de versões, tamanho do arquivo e notas de versão (*Changelog*).
  * Modal com barra de progresso visual em tempo real (`DialogoProgressoDownload`) exibindo MBs baixados e porcentagem.
  * Substituição atômica automática do executável (`.exe`), com reinicialização instantânea na nova versão e preservação 100% integral das configurações do usuário (`config.json`).
