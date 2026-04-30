# Changelog

Histórico de versões do TopBackup.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).

---

## [1.0.6] - 2026-02-12

### Alterado
- App silencioso - removidas notificações de backup
- Pop-ups não aparecem mais após backup automático
- Logging continua funcionando normalmente

---

## [1.0.5] - 2026-02-12

### Corrigido
- **Bug crítico do gbak resolvido** - Backup funcionando corretamente
- Simplificado comando gbak (usa lista de argumentos em vez de string com shell)
- Removida flag `-v` (verbose) que causava problemas
- Usa `-pass` em vez de `-pas`
- Removidas variáveis de ambiente complexas

### Adicionado
- Seleção de pasta do Firebird na interface
- Seleção de pasta do Firebird no Setup Wizard
- Campo para escolher onde está instalado o Firebird

---

## [1.0.4] - 2026-02-11

### Corrigido
- Barra de progresso travando após backup automático
- Melhorada a atualização da interface após backup

---

## [1.0.3] - 2026-02-10

### Alterado
- Removidos pop-ups de verificação de atualização
- Intervalo de checagem ajustado de 6h para 10min (teste)
- Checagem de updates mais silenciosa

---

## [1.0.2] - 2026-02-09

### Corrigido
- Correções menores de estabilidade
- Melhorias no tratamento de erros

---

## [1.0.1] - 2026-02-08

### Adicionado
- Suporte a múltiplas agendas de backup
- Integração com APScheduler
- Sistema de logs rotativos

### Corrigido
- Problemas de codificação UTF-8
- Conexão com MySQL em redes instáveis

---

## [1.0.0] - 2026-02-01

### Adicionado
- Versão inicial do TopBackup
- Backup automático de Firebird 2.5 usando gbak
- Compactação ZIP com 3 modos (Versionado, Semanal, Único)
- Sincronização com MySQL na nuvem
- Upload FTP opcional
- Interface gráfica com CustomTkinter
- Setup Wizard de 4 passos
- Ícone na bandeja do sistema
- Suporte a serviço Windows
- Dashboard Django para monitoramento
- Verificação automática de atualizações

---

## Tipos de Mudança

- **Adicionado** - Funcionalidades novas
- **Alterado** - Mudanças em funcionalidades existentes
- **Depreciado** - Funcionalidades que serão removidas
- **Removido** - Funcionalidades removidas
- **Corrigido** - Correções de bugs
- **Segurança** - Correções de vulnerabilidades
