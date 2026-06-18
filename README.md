# Desafio Técnico — Python + Supabase + Z-API

### Setup da tabela no Supabase

Para executar o projeto, crie a tabela `contatos` no Supabase com o SQL abaixo:
```sql
create table if not exists public.contatos (
  id bigserial primary key,
  nome text not null,
  telefone text not null,
  ativo boolean not null default true,
  created_at timestamptz not null default now()
);
```

Inserindo dados de exemplo:
```sql
insert into public.contatos (nome, telefone, ativo)
values
  ('Ana', '5585988881111', true),
  ('Bruno', '5585988882222', true),
  ('Carla', '5585988883333', true),
  ('Diego', '5585988884444', true);
```

``

A biblioteca #supabase-py permite consultar tabelas expostas pela Data API com chamadas como:

```sql
table("contatos")

select("*")

execute()

```

A documentação também informa que o acesso às tabelas depende das permissões configuradas no projeto.

---

### Variáveis de ambiente (.env)

Crie um arquivo chamado .env na raiz do projeto com as seguintes variáveis:

```
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_KEY=SUA_CHAVE_DO_SUPABASE
```
```
ZAPI_INSTANCE_ID=SUA_INSTANCE_ID
ZAPI_INSTANCE_TOKEN=SEU_INSTANCE_TOKEN
ZAPI_CLIENT_TOKEN=
```
```
MESSAGE_TEMPLATE=Olá, <nome_contato> tudo bem com você?
MAX_CONTACT
```

---

### Explicação das variáveis


SUPABASE_URL: URL do projeto Supabase, utilizada para inicializar o cliente Python.

SUPABASE_KEY: chave da API do Supabase utilizada no backend/script Python.

ZAPI_INSTANCE_ID: identificador da instância criada na Z-API.

ZAPI_INSTANCE_TOKEN: token da instância Z-API, utilizado na URL de autenticação da API.

ZAPI_CLIENT_TOKEN: token opcional de segurança da conta Z-API. Só é necessário se o recurso Account Security Token estiver ativado no painel.

MESSAGE_TEMPLATE: mensagem base que será personalizada com o nome do contato.
MAX_CONTACTS: quantidade máxima de contatos para envio.


O `python-dotenv` procura o arquivo `.env` no diretório atual (ou em diretórios acima) e carrega essas variáveis para o ambiente da aplicação. Também é recomendado manter esse arquivo fora do versionamento, principalmente quando ele contém credenciais.


---

### Como rodar o projeto

Instalação das dependências

```
pip install -r requirements.txt
```

Exemplo de requirements.txt:
```text
supabase
python-dotenv
requests

```

Após configurar o `.env` e instalar as dependências, execute no terminal:

```
python main.py
```

---

### Logs e tratamento de erros

O projeto utiliza o módulo logging do Python para registrar eventos importantes da execução em arquivo e no terminal.
O que é registrado

* início e fim da execução;
* tentativa de leitura de contatos no Supabase;
* quantidade de contatos consultados;
* status da instância Z-API;
* tentativas de envio de mensagem;
* sucessos e falhas no processo;
* mensagens de erro para fins de depuração.

### Arquivo de log

Os logs são gravados no arquivo:

```
logging.log
```

### Objetivo dos logs

O objetivo é facilitar:
* diagnóstico de falhas;
* validação do fluxo ponta a ponta;
* rastreabilidade da execução;
* demonstração de boas práticas no desafio.

### Observação de segurança

Informações sensíveis como tokens, chaves e credenciais não devem ser registradas nos logs.


### Observação

O arquivo `logging.log` enviado no repositório foi gerado a partir de uma execução de teste do fluxo principal, com finalidade de demonstrar o funcionamento


---

### Estrutura do projeto

```text
.
├── .env
├── .env.example
├── .gitignore
├── logging.log
├── main.py
├── README.md
└── requirements.txt
```