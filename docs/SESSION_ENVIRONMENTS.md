# Lantern session environments

Open **Laboratory → Lantern** or run **Lantern: session environments and .tern
checkpoints** from the command palette.

1. Give the session a name and choose Python or Arch Linux.
2. Select **Create session**. Preparation reports progress and offers cancellation.
3. For Python, select **Use in editor** to switch execution, debugging, package
   management and the Python language service to this interpreter. **Console**
   opens an interactive Python prompt. For Arch, **Console** boots the real VM.
4. Select **Save .tern** before ending a session you want to keep.
5. Use **Saved environments → Restore** to reopen it, then open its console or
   activate its Python interpreter.

## What is saved

`experiment.tern` is a versioned JSON descriptor. Its identifier refers to an
owned directory at `.lumen/tern/<id>` in the same workspace. That directory holds
the Python environment or the VM's writable qcow2 overlay and boot seed. Saving
does not embed those files inside the descriptor, snapshot RAM, pause a process,
or make installed Python environments portable between computers.

Keep the descriptor **and its backing directory** to keep the environment.
An Arch overlay also requires its original base image. Arbitrary commands inside
a `.tern` file are never executed. The workspace must be trusted before creating,
activating or opening an environment.

Unsaved backing directories are deleted after their owned processes stop during
normal session/workspace/application closure. Saved directories are retained.
A crash or forced process termination can leave temporary data for later manual
inspection; unknown directories are not deleted on startup.

Python uses a real venv with access to Zénit's bundled base libraries. Additional
packages belong to that environment. This separates dependencies but is not OS
isolation. Ending the active environment returns to the project's `.venv`.

## Reconstructing on another project or station

Schema 2 records exact Python/QEMU versions, the platform, package versions and
an allowlist of preparation actions. Choose **Export environment** to create a
`.tern.zip` containing wheels or an independent QCOW2 disk and boot seed. A saved
descriptor by itself still refers to its original backing directory. Export
refuses a Python inventory changed since saving: save a fresh descriptor first.
Missing wheels and editable packages appear in the report. Downloading missing
wheels from PyPI remains a separate explicit choice.

Copy the archive to the destination project, choose **Check**, review the tools
and missing resources, then choose **Rebuild**. Checking runs in the maintenance
queue and supports cancellation during hashing. It checks package hashes and
wheel compatibility with the actual destination interpreter, in addition to the
exact tool version and platform. A bundle for another platform is not silently
converted. SDK tool installation remains separate.

Rebuilding stages the exact reviewed SHA-256 before running any preparation. If
the original archive changed after review, it refuses to start. It creates a new
owned environment, installs Python dependencies offline with hashes, verifies
versions, and runs `pip check`, including for an empty lock. A failure removes
only this new environment. VM reconstruction verifies an independent QCOW2 disk;
it does not claim that the guest OS has booted.

`reconstruction.json` inside the owned directory records the input archive hash,
a relocation-independent environment identity, the checks performed and their
scope. CoCo execution evidence can refer to this identity when that environment
is active. This is not a snapshot of RAM, processes, external data, credentials,
or the current state of a remote machine.

The automated tests reconstruct actual packages in a separate project/profile
and verify a real independent QCOW2 disk. They run on the same Windows station.
Physical cross-station validation requires a second station and remains pending.

## Virtual machine base

The standard Windows installer contains the Python and native programming base.
QEMU and the Arch cloud image are optional. If they are absent, the Arch option
is disabled. Expand **Configure virtual machine base**, choose a prepared SDK
folder and select **Use this base**. This setting is stored in the local Zénit
profile, not in the project or `.tern` file.

The folder must contain `tool-index.json`, its QEMU executables and the image:

```json
{
  "schema": 1,
  "tools": {
    "qemu-system-x86_64": "qemu/qemu-system-x86_64.exe",
    "qemu-img": "qemu/qemu-img.exe"
  },
  "components": [
    {"id": "arch", "file": "images/Arch-Linux-x86_64-cloudimg.qcow2"}
  ]
}
```

Retain QEMU's supporting DLLs, firmware and notices alongside its executable.
The repository's `tools/prepare_foundation.py` produces this layout as part of
its full developer SDK preparation. An existing prepared SDK can be reused.
`ZENIT_SDK_ROOT` remains supported for source/development setups.

Arch uses QEMU with a serial console and a 16 GiB virtual
disk, one guest CPU and 2 GiB guest RAM. It does not need administrator rights or
host hardware virtualization settings.
The guest has outbound user-mode networking, with no host folders mounted and
no incoming ports forwarded. Shutdown first requests ACPI poweroff, then asks
QEMU to flush and close the disk if the guest does not respond.

Before starting, readiness includes RAM and vCPU reservations of other running
Zénit machines, alongside available RAM and disk space. Closed sessions release
those reservations. The memory check deliberately retains a 20% available-memory
margin; it is a conservative reservation budget rather than a measurement of
the guest's instantaneous RAM use.

Acceleration detection is on demand and cached for up to 60 seconds per QEMU
binary and host. It reads the accelerators supplied by that executable and tests
the host's WHPX, KVM or HVF with a 64 MiB machine, no disk and no network.
The probe starts paused, briefly executes only the supplied BIOS firmware, and
requires a QMP running status before selecting hardware acceleration. This catches
accelerators that initialize but stop in firmware, such as the observed WHPX
"Unexpected VP exit code 4" failure. No guest OS or user program is executed. Otherwise execution uses TCG. This test neither enables
Windows features nor establishes that an imported operating system will boot.

Linux guests receive a rate-limited VirtIO RNG backed by QEMU's built-in entropy
source. New Arch seeds generate an Ed25519 SSH host key instead of the default
set of host-key algorithms, avoiding unnecessary RSA key generation under
software emulation. No keys are fixed or reused between machines. The options
follow the [QEMU invocation reference](https://www.qemu.org/docs/master/system/invocation.html)
and [cloud-init SSH configuration](https://docs.cloud-init.io/en/latest/reference/yaml_examples/ssh.html).

## Hilo and applications

Hilo has one maintenance worker, up to 24 pending operations and bounded job and
discovery caches. It avoids running several package installations at once; it
does not accelerate network downloads, model inference or every filesystem call.

**Settings → Connections** opens installed official tools with explicit user actions. Blender
script execution uses the saved file, so save edits first. Unity needs a project
root; Unreal needs an active `.uproject`. GitHub currently reads metadata only.
AI clients use their own sign-in and permission mechanisms. No provider login
or external application success is fabricated when the client is missing.

Command arguments follow the publishers' interfaces:
[Blender](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html),
[Unity](https://docs.unity.com/en-us/engine/6000.7/manual/unity-editor/command-line-arguments/editor),
[Unreal](https://dev.epicgames.com/documentation/en-us/unreal-engine/command-line-arguments-in-unreal-engine),
and [GitHub CLI](https://cli.github.com/manual/gh_repo_view).
