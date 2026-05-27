# Nail Planner

Sistema web em Python Flask para nail designer controlar clientes, atendimentos e retornos.

## Login padrão

Usuário: `admin`  
Senha: `123456`

## Como rodar no computador

1. Instale o Python.
2. Abra o terminal dentro da pasta do projeto.
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Execute o sistema:

```bash
python app.py
```

5. Abra no navegador:

```txt
http://127.0.0.1:5000
```

## Sobre a página index

A página principal do sistema é o arquivo:

```txt
templates/index.html
```

No Flask, ela aparece quando você acessa `/`.

## Posso hospedar no GitHub Pages?

Não totalmente. GitHub Pages hospeda apenas sites estáticos: HTML, CSS e JavaScript.

Este sistema usa Python Flask e banco SQLite, então precisa de um servidor que rode Python.

Você pode hospedar o código no GitHub como repositório, mas para o sistema funcionar online precisa usar serviços como:

- Render
- Railway
- PythonAnywhere
- VPS
- servidor local com acesso na rede

## Observação importante

O banco `nail_planner.db` será criado automaticamente na primeira vez que o sistema rodar.
