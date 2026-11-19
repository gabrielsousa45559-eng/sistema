# NexoFlow — ERP Omnichannel

Protótipo de interface navegável para o NexoFlow, uma plataforma de gestão que conecta vendas, PDV, financeiro, fiscal, estoque, serviços e gestão. Conceito: do orçamento ao caixa, no balcão, no celular e até sem internet.

## Abrir

No Windows, execute `iniciar.bat`. O script inicia um servidor local e abre o NexoFlow no navegador. O backend usa Python 3 e SQLite integrados, sem instalar pacotes externos. Os dados ficam em `nexoflow.sqlite3` nesta pasta. Se abrir `index.html` diretamente, o protótipo usa o armazenamento local daquele navegador, inclusive sem conexão; para manter os dados num banco SQLite, use o servidor. A fonte DM Sans/Manrope é carregada do Google Fonts quando há conexão.

## Interações disponíveis

- Navegação entre visão geral, vendas, PDV, estoque, notas/XML, financeiro, fiscal, integrações, relatórios, funcionalidades e configurações.
- Catálogo agrupado com os módulos e funções informados: vendas/PDV, financeiro/cobrança, notas fiscais, estoque/compras, serviços/contratos e gestão/plataforma.
- Os quatro atalhos de configurações abrem formulários próprios e persistem no SQLite.
- O botão **Novo pedido** abre o formulário de venda/orçamento. Itens podem ser adicionados; finalizar venda confere saldo e baixa o estoque, enquanto salvar como orçamento preserva o saldo.
- Produtos guardam SKU, código de barras, variação, lote, validade, preço, custo, saldo mínimo e quantidade. Movimentos, vendas e lançamentos são persistidos no SQLite quando o servidor está ativo.
- O saldo é acompanhado por loja. Transferências atualizam as quantidades de origem e destino sem alterar o total da empresa.
- Cotações de fornecedores podem ser registradas e comparadas pelo total; a menor cotação pode ser enviada ao formulário de compra. Compras registram entrada e conta a pagar.
- XML NF-e é lido localmente/servidor e permite vincular itens, registrar entrada no estoque e criar conta a pagar após a conferência.
- Etiquetas imprimíveis incluem EAN-13 válido quando o produto tem código compatível; caso contrário, mostram o SKU. Expedição, OS, contratos, locações, agenda e chamados mantêm histórico de operação.
- Relatórios de vendas, estoque e financeiro podem ser exportados em CSV.
- Busca rápida global com `Ctrl+K` (ou `⌘K`) e busca do menu lateral.
- Tema claro/escuro com preferência salva no navegador.
- Seletor de arquivo XML, que demonstra a seleção local sem enviar o arquivo a um servidor.
- Links de ações principais mostram feedback demonstrativo.

## Estado do projeto

O app local grava vendas, itens, estoque, movimentos, transferências, cotações, operações, lançamentos financeiros, importações XML e configurações. Ainda não possui autenticação multiusuário nem acesso remoto. Emissão fiscal autorizada, assinatura digital com validade jurídica, pagamentos, Open Finance, envio por WhatsApp/SMS, sincronização de marketplaces e geração automática recorrente exigem provedores/credenciais externos e não são afirmados como conectados.
