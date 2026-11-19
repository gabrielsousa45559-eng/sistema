# NexoFlow — checklist para sair do protótipo e entrar em produção

Este documento separa o que já existe no projeto do que precisa ser decidido, implementado ou contratado. Uma tela com botão ou campo de integração não significa que o provedor já esteja conectado.

## Estado atual verificado no código

- Há aplicação web em Python, login, cadastro de empresa/equipe e banco SQLite.
- Vendas, orçamento, produtos, estoque, compras/entrada XML e lançamentos financeiros têm operações locais persistidas.
- O banco principal e bancos de empresas usam arquivos SQLite. No Shard Cloud, o arquivo deve ficar em armazenamento persistente; confirme no painel que `/app` realmente persiste entre reinícios e novas versões.
- Não existe provedor de pagamento conectado. Pix, boleto e cobrança são telas/fluxos demonstrativos.
- Não existe emissão fiscal autorizada integrada à SEFAZ ou ao Emissor Nacional. O XML de compra pode ser importado, mas isso não equivale a emitir nota.
- Marketplaces, banco/Open Finance, WhatsApp/SMS, assinatura digital, e-mail transacional e cobrança recorrente não estão conectados.
- As alegações de venda offline precisam de implementação e validação próprias; o sistema hospedado depende do servidor e do banco online.
- O fluxo de redefinição de senha por e-mail já existe, mas depende de SMTP configurado no servidor. Há bloqueio temporário após cinco tentativas em 15 minutos; confirmação de e-mail, backup/restore automatizado e permissões granulares por módulo ainda faltam.

## Fase 1 — piloto interno da sua empresa

Para testar venda, cadastro e estoque sem emissão fiscal ou cobrança online:

- [ ] Publicar a versão atualizada no Shard Cloud e confirmar HTTPS, domínio e inicialização sem erros.
- [ ] Confirmar armazenamento persistente para o SQLite e para a pasta `tenants/`; reiniciar a aplicação e verificar se os registros continuam lá.
- [ ] Criar o login administrativo usando variáveis secretas do servidor. Não colocar senha no Git, ZIP, código ou conversa.
- [ ] Abrir `/api/health` e confirmar `ok: true` e `superadmin_configured: true`. O diagnóstico não expõe e-mail administrativo nem caminho do banco; use o endereço digitado no login.
- [ ] Cadastrar produtos reais, saldo inicial, preço, custo, clientes e usuários da equipe.
- [ ] Fazer venda de teste, conferir total, baixa de estoque, relatório e acesso de cada usuário.
- [ ] Fazer uma cópia do banco e testar restauração antes de inserir dados importantes.
- [ ] Durante o piloto, emitir documentos fiscais pelo sistema oficial/atual da empresa; não tratar o NexoFlow como emissor fiscal.

**Dados que você precisa decidir/fornecer para configurar o piloto:** domínio/subdomínio que usará, nome da empresa, quais pessoas terão acesso e os dados de catálogo. Credenciais devem ser inseridas diretamente no painel do provedor, nunca enviadas aqui.

## Fase 2 — segurança, dados e operação antes de depender dele

- [ ] Definir backup automático e retenção (diário, cópia fora da VPS e política de recuperação); testar restauração.
- [ ] Confirmar persistência e capacidade de armazenamento da hospedagem; avaliar PostgreSQL gerenciado se houver vários clientes ou uso concorrente significativo.
- [ ] HTTPS obrigatório, cookies seguros, proteção de sessão e segredo de aplicação gerado no servidor.
- [ ] Configurar SMTP e validar o link de recuperação de senha em produção; implementar confirmação de e-mail e ampliar a proteção contra abuso.
- [ ] Revisar isolamento entre empresas em todas as rotas e consultas; impedir que uma empresa leia ou altere dados de outra.
- [ ] Implementar permissões reais por perfil e módulo; hoje os perfis são básicos.
- [ ] Logs de erro, alertas, monitoramento, rotina de atualização e procedimento de indisponibilidade.
- [ ] Revisar exportação, exclusão, retenção e portabilidade dos dados pessoais conforme LGPD; preparar política de privacidade, termos e contratos com clientes com orientação profissional.
- [ ] Executar revisão de segurança e validação funcional antes de carregar dados reais em escala.

## Fase 3 — integrações: escolha o que realmente precisa

Não é necessário contratar tudo para começar. Cada item depende de implementação no backend, testes em sandbox/homologação e configuração das credenciais.

### Pagamentos, Pix e boletos

- [ ] Escolher adquirente/gateway (ex.: Mercado Pago, Asaas ou outro que atenda seu negócio).
- [ ] Criar conta empresarial e aplicação do provedor; obter credenciais de teste e depois produção.
- [ ] Implementar criação de pagamento, consulta de status, cancelamento/estorno e conciliação.
- [ ] Publicar endpoint HTTPS de webhook, validar assinatura/origem, tratar reenvios e eventos duplicados.
- [ ] Se vender assinaturas do próprio NexoFlow, implementar planos, cobranças recorrentes, inadimplência e cancelamento.

**Credenciais normalmente envolvidas:** access token/chave privada, chave pública quando aplicável e segredo de webhook. São segredos; armazenar criptografados no servidor e nunca no navegador ou repositório. O Mercado Pago documenta notificações de pagamento por webhooks e validação de assinatura.

### Documentos fiscais

- [ ] Definir documentos necessários: NF-e/NFC-e de produto, NFS-e de serviço; CT-e/MDF-e só se a operação realmente exigir.
- [ ] Reunir por CNPJ: razão social, endereço, CNPJ, inscrição estadual/municipal, CNAE, regime tributário, série/número fiscal, CFOP, NCM, CEST, CST/CSOSN, alíquotas e regras da operação, com validação do contador.
- [ ] Para NF-e/NFC-e: verificar credenciamento na SEFAZ do estado e obter certificado digital ICP-Brasil compatível (A1 costuma ser mais adequado a servidor; confirmar com contador/fornecedor). O certificado e a senha privada devem ser guardados em cofre de segredos, nunca enviados em chat ou commit.
- [ ] Escolher caminho de integração: provedor fiscal especializado ou integração direta com SEFAZ/Emissor Nacional. Implementar assinatura, transmissão, consulta, cancelamento, inutilização quando aplicável, contingência e armazenamento de XML/DANFE.
- [ ] NFS-e: confirmar município, regime e caminho de emissão aplicável. O padrão nacional tem documentação/API própria e pode exigir credenciamento; verificar regra vigente do município e do contribuinte.
- [ ] Implementar ambiente de homologação, testes de rejeição, autorização e contingência antes de produção.

### E-mail, WhatsApp e SMS

- [ ] E-mail: contratar/configurar serviço transacional, domínio remetente, credencial API/SMTP e registros DNS SPF, DKIM e DMARC. Necessário para convite, confirmação e recuperação de senha.
- [ ] WhatsApp: conta Meta Business, número elegível, app/provedor oficial, templates aprovados, token e webhook; respeitar consentimento e regras de mensagens.
- [ ] SMS: provedor, credencial, remetente e webhook/retornos de entrega.

### Marketplaces e loja virtual

- [ ] Escolher primeiro canal (Mercado Livre, Shopee, Nuvemshop etc.); não tentar integrar todos de uma vez.
- [ ] Criar aplicação de desenvolvedor do canal, cadastrar URLs de retorno HTTPS e obter Client ID/Secret.
- [ ] Implementar OAuth por empresa, renovação/revogação de tokens, webhooks, sincronização de pedidos, produtos, estoque, preço, cancelamentos e idempotência.
- [ ] Fazer testes com conta de teste/sandbox e autorização explícita do lojista. Não pedir senha do marketplace ao usuário.

### Bancos, Open Finance e conciliação

- [ ] Escolher agregador/provedor Open Finance ou começar com importação manual OFX/CSV.
- [ ] Para conexão bancária, passar pelo onboarding e consentimento no provedor; normalmente não se resolve com uma simples chave de API do banco.
- [ ] Implementar importação, associação de transações, aprovação manual, prevenção de duplicidade e trilha de auditoria.

### Assinatura eletrônica

- [ ] Escolher provedor de assinatura, criar conta/aplicação, obter credenciais e configurar webhook.
- [ ] Implementar envio, status, evidências, documentos finais e tratamento de expiração/cancelamento. Assinatura desenhada na tela não substitui integração com provedor.

## Informações para fechar o escopo com você

Responda sem enviar senhas, tokens ou arquivos de certificado:

1. Você quer primeiro **usar o ERP na sua própria empresa** ou também **vender acessos do NexoFlow para outras empresas**?
2. Qual é a atividade da empresa e quais operações fará: produto, serviço ou ambos?
3. Qual cidade/UF e regime tributário? Não envie CNPJ em canal público se preferir; basta confirmar cidade/UF e dizer que os dados fiscais serão passados ao contador/provedor.
4. Quais são indispensáveis no primeiro lançamento: venda/estoque, nota fiscal, Pix, boleto, cobrança recorrente, loja virtual, WhatsApp, banco?
5. Qual domínio já está ligado ao Shard Cloud e qual provedor de pagamento/fiscal você já usa, se houver?

## Sequência recomendada

1. Fazer o piloto interno de venda + estoque com backup confirmado.
2. Corrigir segurança, recuperação de conta e permissões antes de ampliar usuários/clientes.
3. Integrar um provedor fiscal e um de pagamento conforme a atividade da empresa.
4. Só então conectar canais, mensagens, Open Finance e automações.
5. Para transformar em SaaS vendável a terceiros, concluir isolamento, billing, suporte, monitoramento, termos/LGPD e plano de resposta a incidentes.

## Referências oficiais consultadas

- Portal Nacional NFS-e — documentação técnica atual: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual
- Serviço NFS-e Nacional — API e credenciamento: https://www.gov.br/pt-br/servicos/emitir-nota-fiscal-de-servico-eletronica?id=20995&origem=servico
- Portal NF-e — certificado digital e assinatura: https://www.nfe.fazenda.gov.br/pOrtaL/perguntasFrequentes.aspx?AspxAutoDetectCookieSupport=1&tipoConteudo=FBya9bipr34%3D
- Mercado Pago — webhooks e pagamentos: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/payment-notifications
- Mercado Livre — OAuth e credenciais: https://developers.mercadolivre.com.br/pt_br/conheca-as-novidades-que-os-vendedores-recebem/gestao-de-identidades-e-acessos-oauth-e-tokens
- ANPD — guia orientativo LGPD: https://www.gov.br/anpd/pt-br/assuntos/noticias/guia_lgpd_final.pdf
