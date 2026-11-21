# NfSplit 📄💳

> **Separador Inteligente de Notas Fiscais (DANFEs), Boletos Bancários e Documentos de Carga**  
> *Versão 1.1.0 • 100% Offline • Sem Servidor • Executável Nativo (.exe) para Windows*

---

## 🚀 Sobre o Projeto

O **NfSplit** é uma solução profissional para transportadoras, departamentos fiscais, escritórios contábeis e setores de faturamento que recebem arquivos PDF únicos contendo dezenas de páginas mescladas (DANFEs, Boletos de cobrança, Mapas de Entrega e Acertos de Carga).

O sistema processa o arquivo PDF em nível de fluxo binário (*lossless*), classificando cada página, mantendo a nitidez original dos códigos de barras e organizando os arquivos renomeados de forma padronizada.

---

## ✨ Principais Recursos

* **100% Offline e Local**: Não requer conexão com a internet para processar arquivos. Nenhum dado fiscal sai da sua máquina.
* **Executável Único Portátil (`NfSplit.exe`)**: Não requer instalação prévia de Python ou outros pacotes. Basta abrir e usar.
* **Interface Gráfica Suavizada**: Desenvolvida com *CustomTkinter*, trazendo cantos arredondados, cartões suaves e experiência visual moderna.
* **Caixas de Diálogo Integradas**: Todas as mensagens de sucesso, alerta, erro e confirmações são desenhadas dentro da própria aplicação (sem usar alertas cinzas do Windows).
* **DANFEs Multi-página**: Reconhece automaticamente quando uma DANFE ocupa mais de uma página (ex: 2/2, 3/3) e agrupa as páginas no mesmo arquivo.
* **Extração por Chave de Acesso (44 dígitos)**: Obtém o número exato da NF a partir do código numérico `chave[25:34]`, eliminando erros de leitura do cabeçalho.
* **Leitor Universal de Boletos FEBRABAN**:
  * Identificação de bancos (Banco do Brasil, Bradesco, Itaú, Santander, Caixa, Sicoob, Sicredi, Safra, etc.).
  * Extração exata do valor em centavos e data de vencimento.
  * Identificação de parcela (ex: 01/01, 01/03).
* **Junção Inteligente (Nota + Boleto)**: Opção de juntar automaticamente a DANFE e o Boleto correspondente em um único PDF por cliente.
* **Documentos de Carga**: Separa e preserva Mapas de Entrega e Acertos de Carga.
* **Relatório em Planilha Excel (`relatorio.csv`)**: Gera relatório automático com codificação UTF-8 com BOM, contendo todos os dados fiscais e financeiros.
* **Sistema de Atualizações OTA**: Módulo de verificação e instalação *Over-The-Air* integrado, pronto para conexão com servidor de distribuição futuro.

---

## 🖥️ Como Usar

1. Dê um duplo clique no arquivo **`NfSplit.exe`**.
2. Na primeira execução, o sistema solicitará onde você deseja salvar os arquivos organizados (essa pasta ficará gravada para os próximos usos).
3. Clique em **"📂 Selecionar PDF"** e escolha o arquivo da carga (ou selecione uma pasta inteira de PDFs).
4. Ajuste as opções conforme desejar:
   * *Juntar Nota + Boleto em PDF único*.
   * *Salvar Mapas de Entrega e Acertos de Carga*.
   * *Limpar CNPJ da Razão Social*.
5. Clique no botão **"⚡ PROCESSAR E SEPARAR ARQUIVOS"**.
6. Ao término, a tabela exibirá o resumo completo e a caixa de diálogo nativa permitirá abrir a pasta com 1 clique.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem**: Python 3.11+
* **Interface Gráfica**: CustomTkinter 6.0+
* **Manipulação e Extração de PDF**: PyPDF 7.1+, pdfplumber 0.11+
* **Processamento de Imagens e Ícones**: Pillow 13.0+
* **Compilação**: PyInstaller 6.22+

---

## 📋 Changelog e Versões

Consulte o arquivo [CHANGELOG.md](CHANGELOG.md) para o histórico detalhado de alterações e notas de versão.

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais detalhes.
