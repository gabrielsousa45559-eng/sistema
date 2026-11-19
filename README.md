# NexoFlow — ERP Omnichannel

Protótipo de interface navegável para o NexoFlow, uma plataforma de gestão que conecta vendas, PDV, financeiro, fiscal, estoque, serviços e gestão. Conceito: do orçamento ao caixa, no balcão, no celular e até sem internet.

## Abrir

No Windows, execute `iniciar.bat`. O script inicia um servidor local e abre o NexoFlow no navegador. O backend usa Python 3 e SQLite integrados, sem instalar pacotes externos. Os dados ficam em `nexoflow.sqlite3` nesta pasta. A fonte DM Sans/Manrope é carregada do Google Fonts quando há conexão.

## Interações disponíveis

- Navegação entre visão geral, vendas, PDV, estoque, notas/XML, financeiro, fiscal, integrações, relatórios, funcionalidades e configurações.
- Catálogo agrupado com os módulos e funções informados: vendas/PDV, financeiro/cobrança, notas fiscais, estoque/compras, serviços/contratos e gestão/plataforma.
- Os quatro atalhos de configurações abrem formulários próprios e persistem no SQLite.
- Produtos, movimentações, vendas e lançamentos financeiros são persistidos no SQLite. Vendas validam saldo e baixam estoque na mesma transação.
- XML NF-e é lido no servidor local e permite registrar entrada no estoque e conta a pagar após a conferência.
- Relatórios de vendas e estoque podem ser exportados em CSV.
- Busca rápida global com `Ctrl+K` (ou `⌘K`) e busca do menu lateral.
- Tema claro/escuro com preferência salva no navegador.
- Seletor de arquivo XML, que demonstra a seleção local sem enviar o arquivo a um servidor.
- Links de ações principais mostram feedback demonstrativo.

## Estado do projeto

O app local já grava vendas, itens, estoque, movimentos, lançamentos financeiros, importações XML e configurações. Ainda não possui autenticação multiusuário nem acesso remoto. Emissão fiscal real, pagamentos, Open Finance, WhatsApp/SMS e sincronização de marketplaces precisam de credenciais e provedores externos; não são simulados como se estivessem conectados. Configure provedores antes de usar em produção.
