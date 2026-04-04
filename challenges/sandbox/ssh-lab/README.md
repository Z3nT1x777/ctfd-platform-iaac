# SSH Lab

## Overview

This is a minimal SSH-based challenge example for the template repository.
It exists to demonstrate non-web access rendering and container_port handling.

## Connection

The launch card should render an SSH command, for example:

```bash
ssh ctf@192.168.56.10 -p 5003
```

Password for this template example:

```text
ctf
```

## Notes

- The Docker container exposes SSH on port 22.
- Host port is mapped to `5003` to stay inside the validation range.
- `app.py` is a placeholder kept for compatibility with the repository validator.
