# Soluce — 01-python-obfusc

## Contexte

Un script Python a été obfusqué : les noms de variables ont été remplacés par `_0`, `_1`, etc. Le flag est encodé en hexadécimal, découpé en morceaux concaténés.

## Code obfusqué analysé

```python
_0=print;_1=input;_3=lambda x:bytes.fromhex(x).decode()
_4='4354467b'+'657865635f'+'6261736536'+'345f756e70'+'61636b7d'
_5=_3(_4)
_6=_1("Password: ")
if _6==_5:_0("Correct! "+_5)
else:_0("Wrong!")
```

## Étapes de résolution

### Étape 1 — Renommer les variables

```python
# _0 = print
# _1 = input
# _3 = fonction de décodage hex
decode = lambda x: bytes.fromhex(x).decode()

# _4 = chaîne hex concaténée
hex_str = '4354467b' + '657865635f' + '6261736536' + '345f756e70' + '61636b7d'

# _5 = flag décodé
flag = decode(hex_str)

# _6 = saisie utilisateur
user_input = input("Password: ")

if user_input == flag:
    print("Correct! " + flag)
else:
    print("Wrong!")
```

### Étape 2 — Décoder la chaîne hex

```python
# Concaténer les morceaux
full_hex = '4354467b657865635f6261736536345f756e7061636b7d'

# Décoder en Python
flag = bytes.fromhex(full_hex).decode()
print(flag)
# CTF{exec_base64_unpack}
```

### Méthode ligne de commande

```bash
# Python one-liner
python3 -c "print(bytes.fromhex('4354467b657865635f6261736536345f756e7061636b7d').decode())"

# Ou avec xxd
echo '4354467b657865635f6261736536345f756e7061636b7d' | xxd -r -p
```

### Correspondance hexadécimale

| Hex | ASCII |
|-----|-------|
| `4354467b` | `CTF{` |
| `657865635f` | `exec_` |
| `6261736536` | `base6` |
| `345f756e70` | `4_unp` |
| `61636b7d` | `ack}` |

## Correction

En concaténant les fragments hexadécimaux et en les décodant :

```
4354467b + 657865635f + 6261736536 + 345f756e70 + 61636b7d
= 4354467b657865635f6261736536345f756e7061636b7d
= CTF{exec_base64_unpack}
```

**Flag : `CTF{exec_base64_unpack}`**
