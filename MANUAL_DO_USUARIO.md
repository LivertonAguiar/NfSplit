# Manual do Usuário - NfSplit v1.0.0

Este guia orienta o usuário passo a passo sobre a utilização completa do aplicativo **NfSplit**.

---

## 1. Instalação e Execução

O **NfSplit** é um programa portátil. Isso significa que ele não requer nenhum processo de instalação complexo nem permissões de administrador.

1. Baixe ou copie o arquivo **`NfSplit.exe`** para o seu computador (recomendamos manter na Área de Trabalho ou em uma pasta de sua preferência).
2. Dê um duplo clique no arquivo para iniciar o programa.
3. Não há necessidade de conexão com a internet para processar arquivos.

---

## 2. Primeira Execução e Definição da Pasta de Saída

Para manter seu computador organizado, o sistema solicitará onde você prefere salvar os arquivos processados:

1. Se nenhuma pasta tiver sido configurada, ao iniciar o processamento, uma janela nativa do programa perguntará:
   > *"📁 Onde deseja salvar os arquivos processados?"*
2. Escolha o diretório desejado (por exemplo, `C:\Notas_Separadas` ou `Área de Trabalho\Notas`).
3. Uma vez selecionada, **esta pasta ficará gravada para todos os usos futuros**, não sendo necessário escolher novamente a cada execução.
4. Caso queira trocar a pasta no futuro, basta clicar no botão **"Alterar Pasta"** na tela principal ou na janela de **Configurações**.

---

## 3. Seleção de Arquivos para Separação

O NfSplit suporta dois modos de entrada:

* **Arquivo Individual**: Clique no botão **"📂 Selecionar PDF"** para escolher um único arquivo de carga (ex: `CARGA_16952.pdf`).
* **Lote / Pasta Inteira**: Clique no botão **"📁 Pasta Inteira"** caso possua diversos arquivos PDF para processamento em massa.

---

## 4. Opções de Processamento

Antes de clicar em processar, você pode personalizar o comportamento:

* **Juntar Nota + Boleto em PDF único**:
  Quando habilitado, o sistema localiza a DANFE e o(s) boleto(s) emitidos para o mesmo cliente e os une em um único PDF (ex: `NF 138820 - AUTO POSTO.pdf`).
* **Salvar Mapas de Entrega e Acertos de Carga**:
  Quando ativado, os documentos de romaneio, mapas de entrega e acertos da transportadora são salvos em arquivos separados identificados pelo número da carga.
* **Limpar CNPJ da Razão Social**:
  Remove automaticamente prefixos numéricos de CNPJ do início do nome da empresa para gerar nomes de arquivos limpos e legíveis.

---

## 5. Processamento e Resultados

1. Clique no botão azul **"⚡ PROCESSAR E SEPARAR ARQUIVOS"**.
2. A barra de progresso animada indicará o processamento em tempo real.
3. Ao finalizar, uma caixa de diálogo nativa apresentará o tempo de execução e as quantidades processadas.
4. Clique em **"📂 Abrir Pasta Gerada"** para ir diretamente aos arquivos no Windows Explorer.
5. Um arquivo chamado **`relatorio.csv`** será criado dentro da pasta de saída, pronto para ser aberto no Microsoft Excel.

---

## 6. Configurações e Preferências Padrão

Clique no botão **"⚙ Configurações"** no topo superior direito para:
* Alterar o comportamento padrão de inicialização do sistema;
* Redefinir a pasta de saída padrão;
* Restaurar os padrões originais de fábrica.

---

## 7. Atualizações OTA (Over-The-Air)

O NfSplit possui arquitetura integrada para receber atualizações automáticas via rede local ou servidor de distribuição. Por padrão na versão 1.0.0, este módulo permanece inativo até que a URL de atualização seja configurada pelo administrador do sistema.
