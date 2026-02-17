# Contribuindo

Quer ajudar no projeto? Massa. Aqui tem as diretrizes.

---

## Reportando Bugs

Antes de abrir uma issue:

1. Confere se já não tem uma issue aberta pro mesmo problema
2. Tenta reproduzir com a versão mais recente
3. Coleta as informações necessárias

**Na issue, inclui:**
- Versão do TopBackup (aparece na janela principal)
- Versão do Windows
- O que você fez (passos pra reproduzir)
- O que esperava que acontecesse
- O que aconteceu de verdade
- Trecho relevante do log (`C:\TOPBACKUP\logs\topbackup.log`)

Quanto mais detalhes, mais rápido a gente resolve.

---

## Sugerindo Features

Abre uma issue com:

1. O problema que a feature resolve
2. Como você imagina a solução
3. Alternativas que você considerou

Não precisa ser detalhado demais. A gente discute na issue.

---

## Mandando Pull Request

### Antes de começar

1. Abre uma issue descrevendo o que você quer fazer
2. Espera um feedback pra confirmar que faz sentido
3. Daí sim começa a codar

Isso evita trabalho jogado fora.

### Setup de desenvolvimento

**TopBackup:**
```bash
# Clona
git clone https://github.com/seuuser/topbackup.git
cd topbackup/TopBackup

# Ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instala dependências
pip install -r requirements.txt

# Roda
python src/main.py
```

**Dashboard:**
```bash
cd dashboard-clientes
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

### Fazendo o PR

1. Cria uma branch descritiva:
   ```bash
   git checkout -b fix/gbak-timeout
   git checkout -b feature/email-notifications
   ```

2. Faz commits pequenos e descritivos:
   ```
   fix: aumenta timeout do gbak pra 2 horas
   feat: adiciona notificação por email após backup
   docs: atualiza FAQ com pergunta sobre restore
   ```

3. Testa suas mudanças

4. Abre o PR com:
   - Descrição do que faz
   - Qual issue resolve (se tiver)
   - Como testar

---

## Padrões de Código

### Python (TopBackup)

- Python 3.10+
- Type hints nas funções públicas
- Docstrings em português
- Snake_case pra variáveis e funções
- PascalCase pra classes

```python
def calcular_tamanho_formatado(bytes: int) -> str:
    """
    Converte bytes pra formato legível (KB, MB, GB).

    Args:
        bytes: Tamanho em bytes

    Returns:
        String formatada tipo "1.5 MB"
    """
    ...
```

### Django (Dashboard)

- Django 6.0+
- Views baseadas em classe quando faz sentido
- Services separados da view (lógica de negócio em services.py)
- Templates com herança (base.html)

### Geral

- Commits em português ou inglês (consistente no PR)
- Não commita secrets, .env, config.json com senhas
- Testes são bem-vindos (mas não obrigatórios por enquanto)

---

## Estrutura de Branches

- `main` - Versão estável
- `develop` - Desenvolvimento (se tiver)
- `feature/*` - Novas funcionalidades
- `fix/*` - Correções de bugs
- `docs/*` - Documentação

---

## Checklist do PR

- [ ] Código segue os padrões do projeto
- [ ] Testei as mudanças localmente
- [ ] Atualizei a documentação se necessário
- [ ] Não tem secrets no código
- [ ] Issue relacionada linkada (se aplicável)

---

## Dúvidas?

Abre uma issue com a tag `question` ou comenta no PR.
