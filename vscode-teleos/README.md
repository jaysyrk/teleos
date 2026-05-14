# Teleos — VS Code Extension

Language support for `.teleos` logic files.

## Features

- **Syntax highlighting** — keywords (`fact:`, `rule:`, `ask:`, `why:`, `all:`, `assert:`, `import:`), variables (ALL CAPS), comparisons (`>`, `<=`, etc.), numbers, and comments
- **Snippets** — `fact`, `rule`, `rulea`, `rulen`, `ask`, `why`, `all`, `assert`, `assertn`, `import`, `rulenum`
- **File icons** — `.teleos` files get a distinctive icon in the explorer

## Example

```teleos
# Access control rules

import: base-people.teleos

fact: document is confidential
rule: if X is admin then X can access Y
rule: if X is user and not X is banned then X can access Y

ask:  alice can access document
why:  bob can access document
all:  WHO can access document

assert:     alice can access document
assert not: charlie can access document
```

## Installing

Install from the VS Code Marketplace or build locally:

```bash
npm install -g @vscode/vsce
cd vscode-teleos
vsce package
code --install-extension teleos-0.1.0.vsix
```
