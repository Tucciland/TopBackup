# FAQ

Perguntas frequentes sobre o TopBackup e Dashboard.

---

## Geral

### Qual a licença?

MIT. Pode usar, modificar, distribuir. Só não remove os créditos.

---

### Funciona com Firebird 3 ou 4?

Na real, não. O TopBackup foi feito especificamente pro Firebird 2.5. O gbak mudou bastante nas versões mais novas, então não é garantido que funcione.

Se precisar suportar Firebird 3+, abre uma issue que a gente avalia.

---

### Roda em Linux?

O Dashboard sim (Django é multiplataforma).

O TopBackup não - ele é feito pra Windows (usa PyWin32 pro serviço, caminhos Windows, etc). Não tem planos de portar pro Linux por enquanto, já que Firebird 2.5 + sistema legado geralmente roda em Windows mesmo.

---

### As senhas ficam em texto plano?

Sim, tá em texto plano no config.json. O lance é que o arquivo fica no servidor do cliente, protegido por permissões de arquivo do Windows.

É um sistema legado que conecta num Firebird 2.5, então assumimos que já tem outras medidas de segurança na rede. Encriptação de config é um nice-to-have pra versões futuras.

---

### Precisa de internet pra fazer backup?

Não. O backup local funciona offline.

Mas pra sincronizar com o Dashboard (MySQL na nuvem), precisa de internet. Se tiver offline, o backup acontece normal, só não registra no Dashboard até voltar a conexão.

---

## TopBackup

### Posso fazer backup com o sistema (ERP) aberto?

Sim. O gbak faz backup "quente" - ele cria uma snapshot do banco e faz backup dela. Usuários podem continuar trabalhando.

Porém, recomenda-se fazer backup em horários de baixo uso pra não impactar performance.

---

### E se a internet cair no meio do backup?

O backup local continua normal. Só o upload pro FTP e a sincronização MySQL que falham.

Na próxima execução (ou quando a internet voltar), ele sincroniza os logs pendentes.

---

### Como faço restore?

O TopBackup só faz backup, não faz restore automático.

Pra restaurar, você usa o gbak manualmente:

```bash
# Restore pra novo banco
gbak -c -user SYSDBA -pass masterkey C:\Backups\backup.fbk C:\Dados\BANCO_NOVO.FDB

# Ou descompacta o ZIP primeiro e depois roda o comando acima
```

Se liga: `-c` cria um banco novo. Não restaura em cima de um banco existente.

---

### Posso ter múltiplos horários de backup?

Sim. Basta cadastrar mais de uma linha na tabela AGENDA_BACKUP do Firebird.

Tipo: uma agenda pras 12h (backup de almoço) e outra pras 23h (backup noturno).

---

### O que acontece se o backup falhar?

1. O status fica como "F" (falha) no LOG_BACKUPS
2. A mensagem de erro é gravada em MENSAGEM_ERRO
3. No Dashboard, a empresa aparece em vermelho
4. O próximo backup agendado roda normalmente

Não tem retry automático por enquanto. Se falhou, só no próximo horário.

---

### Como atualizo pra nova versão?

Se `auto_update` tá true no config.json:
1. O app verifica automaticamente
2. Se tiver versão nova, avisa e pergunta se quer atualizar
3. Baixa, substitui e reinicia

Manual:
1. Para o TopBackup (ou serviço)
2. Substitui o .exe pela versão nova
3. Inicia novamente

---

### Posso rodar múltiplas instâncias?

Não é recomendado. Cada instalação deve fazer backup de um banco específico.

Se tiver múltiplos bancos pra backupear, o ideal é:
- Uma instalação por banco, ou
- Configurar múltiplas entradas na AGENDA_BACKUP apontando pro mesmo banco

---

## Dashboard

### O Dashboard suporta multi-tenant?

Sim. Cada empresa tem seu registro em EMPRESA e seus backups em LOG_BACKUPS. O Dashboard mostra todas as empresas cadastradas.

Não tem isolamento por usuário/login (ainda). Quem acessa o Dashboard vê todas as empresas.

---

### Por que managed = False nos models?

Porque as tabelas são criadas e gerenciadas pelo TopBackup, não pelo Django.

O Django só lê os dados. Ele não faz migrations nessas tabelas, não cria, não altera estrutura.

---

### Posso adicionar campos nos models?

Pode, mas com cuidado:

1. Se adicionar campo novo no Django, precisa adicionar na tabela MySQL também
2. Se o TopBackup não conhecer o campo, ele não vai preencher
3. Melhor sincronizar: atualiza Django e TopBackup juntos

---

### Como funciona a classificação de status?

```
OK         = último backup foi há menos de 24h
ATENCAO    = último backup foi entre 24h e 48h atrás
VERIFICAR  = sem backup há mais de 48h
FALHA      = último backup teve status = 'F'
EXECUTANDO = backup em andamento (status = 'E')
```

A prioridade de exibição nos cards é: Falha > Verificar > Sem dados > Atenção > OK.

---

### Os dados atualizam em tempo real?

Quase. O Dashboard faz AJAX a cada X segundos pra atualizar os cards. Não é WebSocket em tempo real, mas é suficiente pro caso de uso.

---

### Posso exportar relatórios?

Ainda não tem funcionalidade de exportação (CSV, PDF). Tá na lista de features futuras.

Por enquanto, você pode consultar direto no MySQL:

```sql
-- Backups da última semana
SELECT e.FANTASIA, l.DATA_INICIO, l.STATUS, l.TAMANHO_FORMATADO
FROM LOG_BACKUPS l
JOIN EMPRESA e ON e.ID = l.ID_EMPRESA
WHERE l.DATA_INICIO >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY l.DATA_INICIO DESC;
```

---

## Problemas Comuns

### "Meu TopBackup não aparece no Dashboard"

1. Verifica se sincronizou (olha se tem empresa_id no config.json)
2. Confere se o CNPJ tá certo
3. No Dashboard, vê se a empresa tá com ATIVO = 'S'

---

### "O backup tá demorando muito"

Bancos grandes demoram mesmo. Um banco de 2GB pode levar 10-15 minutos.

Se demorar mais de 1 hora, vai dar timeout. Considera fazer backup em horário com menos uso do banco.

---

### "Quero mudar o destino do backup"

Duas opções:
1. Edita o config.json (seção backup > local_destino1)
2. Ou edita a tabela AGENDA_BACKUP no Firebird (campo LOCAL_DESTINO1)

A agenda do Firebird tem prioridade sobre o config.json.
