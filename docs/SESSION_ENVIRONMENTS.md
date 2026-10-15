# Lantern session environments

Open **Laboratory → Lantern** or run **Lantern: session environments and .tern
checkpoints** from the command palette.

1. Give the session a name and choose Python or Arch Linux.
2. Select **Create session**. Hilo shows preparation progress and cancellation.
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
inspection; R12 does not delete unknown directories on startup.

Python uses a real venv with access to Zénit's bundled base libraries. Additional
packages belong to that environment. This separates dependencies but is not OS
isolation. Ending the active environment returns to the project's `.venv`.

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

Arch uses QEMU software virtualization (TCG), a serial console, a 16 GiB virtual
disk, one guest CPU and 2 GiB guest RAM. It does not need administrator rights or
host hardware virtualization. Cold boot is slower than hardware acceleration.
The guest has outbound user-mode networking, with no host folders mounted and
no incoming ports forwarded. Shutdown first requests ACPI poweroff, then asks
QEMU to flush and close the disk if the guest does not respond.

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
