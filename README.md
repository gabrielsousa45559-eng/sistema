# NexoFlow — ERP Omnichannel

Protótipo de interface navegável para o NexoFlow, uma plataforma de gestão que conecta vendas, PDV, financeiro, fiscal, estoque, serviços e gestão. Conceito: do orçamento ao caixa, no balcão, no celular e até sem internet.

## Abrir

No Windows, execute `iniciar.bat`. O script inicia o backend Python e abre a página comercial. O backend usa Python 3 e SQLite integrados, sem pacotes Python externos. Os dados centrais ficam em `nexoflow.sqlite3`; novas empresas recebem arquivos separados em `tenants/`. Criação de contas e login precisam do servidor.

### Publicar em VPS / hospedagem Node

Instale Python 3 no servidor e use `npm start` (ou `node server.js`) como comando de inicialização. O `server.js` detecta Python e inicia `server.py`; configure a variável `PORT` disponibilizada pela hospedagem. Não use `node server.py`, pois esse arquivo contém código Python. Configure `NEXOFLOW_SUPERADMIN_EMAIL` e `NEXOFLOW_SUPERADMIN_PASSWORD` no ambiente da VPS antes da primeira inicialização para criar o acesso global. Coloque o serviço atrás de HTTPS/reverse proxy e mantenha o arquivo SQLite em disco persistente.

### Publicar no Shard Cloud

Envie o arquivo `sistema-shardcloud.zip` como uma aplicação **Python** (não Node.js). O ZIP de deploy precisa conter `.shardcloud`, `requirements.txt` e `main.py`; esses arquivos já estão no projeto. O `.shardcloud` aponta para `main.py`, que escuta na porta 80. No formulário do Shard, escolha Python e não selecione `app.js` como arquivo principal. Cadastre `NEXOFLOW_SUPERADMIN_EMAIL` e `NEXOFLOW_SUPERADMIN_PASSWORD` nas variáveis da aplicação. O SQLite precisa ficar no armazenamento persistente `/app`.

A página comercial está em `sales-page.html`, com preços demonstrativos e inscrição. **Já uso o NexoFlow** abre `login.html`; **Criar conta** abre `signup.html`. O cadastro escolhe um plano e cria uma empresa isolada. Os preços não têm cobrança automática integrada.

Cada empresa cria seu administrador pelo cadastro público; esse administrador cria acessos da equipe em **Configurações → Usuários e permissões**. Para controlar toda a plataforma, configure `NEXOFLOW_SUPERADMIN_EMAIL` e `NEXOFLOW_SUPERADMIN_PASSWORD` (mínimo de 8 caracteres) no servidor antes da inicialização. O superadmin entra em `/admin.html` para controlar empresas, contas, planos, preços e atividade.

## Interações disponíveis

- Navegação entre visão geral, vendas, PDV, estoque, notas/XML, financeiro, fiscal, integrações, relatórios, funcionalidades e configurações.
- Catálogo agrupado com os módulos e funções informados: vendas/PDV, financeiro/cobrança, notas fiscais, estoque/compras, serviços/contratos e gestão/plataforma.
- Os quatro atalhos de configurações abrem formulários próprios e persistem no SQLite.
- Cadastro de empresa e login por senha, com banco SQLite separado por cliente. Senhas usam PBKDF2-HMAC-SHA256 e sessões expiram em 12 horas.
- A área **Usuários e permissões** cria acessos da equipe da empresa, permite ativar/suspender contas e registra alterações e logins.
- Painel separado de **Superadmin** para controlar empresas, usuários globais, planos, preços e logs. O `iniciar.bat` local usa `127.0.0.1`; o iniciador Node usa `0.0.0.0` e `PORT` para hospedagem, devendo ficar atrás de HTTPS/reverse proxy.
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

Ainda faltam cobrança automática, confirmação de e-mail, recuperação de senha, limite de tentativas e permissões detalhadas por módulo. Os preços são demonstrativos. Emissão fiscal autorizada, assinatura digital com validade jurídica, pagamentos, Open Finance, WhatsApp/SMS, marketplaces e rotinas recorrentes precisam de provedores/credenciais externos.
