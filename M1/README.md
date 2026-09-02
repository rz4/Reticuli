# Reticuli

Sealed, reproducible records of model-assisted work. The invariant is the three-machine test.

![logo.png](logo.png)

## What is it?

Reticuli records computational work with cryptographic certainty. Every record carries proof: the root equals the hash of its inputs and execution. You can verify the record independently, audit its gates, and know with confidence what actually happened.

The three-machine test is the core: you can reproduce the work on three independent machines and get identical roots.

## Install

```
pip install "git+https://github.com/rz4/reticuli"
```

## Quick start

Initialize a new session:

```
ret init
```

Wire your project's agent to the trace:

```
ret hooks
```

Run a command and record it:

```
ret run <command>
```

View your session's record:

```
ret show
```

Verify the record holds on this machine:

```
ret verify
```

Audit the gates that were recorded:

```
ret audit
```

Rehydrate the record in a clean room:

```
ret realize
```

Run the three-machine test:

```
ret prove
```

Export the record as a tarball:

```
ret export
```

Import a record from a tarball:

```
ret import
```

Check the workspace through Reticuli's lens:

```
ret tree
```

## The core idea

Every Reticuli record is defined by its root. The root is a hash of the record's inputs and execution:

```
root = hash(inputs, execution, gates)
```

This root must be identical across all three machines. If it changes, the record is invalid.

## Learn more

Read the full guide: [docs/guide.md](docs/guide.md)

---

**Reticuli** — sealed records for reproducible work.
