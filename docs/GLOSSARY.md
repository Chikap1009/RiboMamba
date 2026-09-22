# Glossary — RiboMamba

Every technical term used in this project, defined once. Format per entry:

- **Definition:** one plain-language sentence.
- **Analogy:** from everyday life or electronics.
- **Where it appears:** in our code or docs. ("Not yet in code" is fine early on.)
- **First explained:** logbook reference.

Sections: Biology · Machine learning · Maths · Software.

---

## Biology

### Molecule
- **Definition:** A group of atoms held together by chemical bonds, acting as one physical object.
- **Analogy:** A soldered assembly. Individual components (atoms) joined into one unit that behaves as a whole.
- **Where it appears:** Not yet in code.
- **First explained:** session 01.

### Polymer
- **Definition:** A long molecule made by linking many similar small units end to end in a chain.
- **Analogy:** A chain of beads, or a shift register made of identical flip-flop stages.
- **Where it appears:** Not yet in code.
- **First explained:** session 01.

### DNA (deoxyribonucleic acid)
- **Definition:** The cell's long-term storage molecule for genetic instructions. Usually two strands wound together; uses the letters A, C, G, T.
- **Analogy:** ROM. The master copy the cell never executes from directly.
- **Where it appears:** Not in code. Mentioned only to contrast with RNA.
- **First explained:** session 01.

### RNA (ribonucleic acid)
- **Definition:** A single-stranded chain molecule copied from DNA, written in the letters A, C, G, U. Some RNAs carry instructions to build proteins; others fold into shapes and do jobs themselves.
- **Analogy:** A working copy loaded from ROM into RAM. Some copies are read; some *become* little machines.
- **Where it appears:** Everything. Our model generates RNA sequences.
- **First explained:** session 01.

### Nucleotide
- **Definition:** One link in an RNA (or DNA) chain: a backbone piece (sugar + phosphate) with one base attached.
- **Analogy:** One stage of a shift register. Identical hardware, but it holds one symbol.
- **Where it appears:** Each nucleotide will become one *token* in our model (explained in Phase 1).
- **First explained:** session 01.

### Base (nucleobase)
- **Definition:** The variable part of a nucleotide. In RNA it is one of four: A (adenine), U (uracil), G (guanine), C (cytosine).
- **Analogy:** The value stored in a register stage. The stage is always the same; the value changes.
- **Where it appears:** Our vocabulary of 4 letters (plus special tokens later).
- **First explained:** session 01.

### Backbone (sugar-phosphate backbone)
- **Definition:** The repeating, identical chain of sugar and phosphate groups that holds the bases in order.
- **Analogy:** A PCB trace or bus that connects the stages. It carries no data itself; it only fixes the order.
- **Where it appears:** Not in code. We model only the sequence of bases.
- **First explained:** session 01.

### Sequence
- **Definition:** The ordered list of bases in an RNA, written as a string, e.g. `GGGAAACCC`.
- **Analogy:** A serial bitstream, where each symbol carries 2 bits (4 possibilities).
- **Where it appears:** The input and output of our model.
- **First explained:** session 01.

### 5′ end and 3′ end ("five-prime", "three-prime")
- **Definition:** The two ends of an RNA chain, which are chemically different, so the chain has a direction. Sequences are written 5′ → 3′, left to right, by convention.
- **Analogy:** MSB-first vs LSB-first in a serial protocol. Reading the same bits in the opposite order gives a different word.
- **Where it appears:** All our sequences are stored in 5′ → 3′ order.
- **First explained:** session 01.

### Protein
- **Definition:** A different kind of chain molecule (made of 20 kinds of "amino acids") that does most of the work in a cell. Built by reading certain RNAs.
- **Analogy:** The finished product the factory manufactures from the instruction sheet.
- **Where it appears:** Not in code. Mentioned for context only.
- **First explained:** session 01.

### Covalent bond
- **Definition:** A strong chemical bond where atoms share electrons. It does not break at body temperature. It is what links the RNA backbone.
- **Analogy:** A solder joint: permanent under normal operating conditions.
- **Where it appears:** Not in code. It is why the sequence *order* never changes.
- **First explained:** session 01.

### Hydrogen bond
- **Definition:** A weak attraction between specific atoms on two bases. Weak enough that random thermal jiggling can break it.
- **Analogy:** One hook of Velcro: it holds, but not firmly.
- **Where it appears:** Not in code. It is the physical reason base pairs exist.
- **First explained:** session 01.

### Base pair
- **Definition:** Two bases, at different positions in the chain, held together by hydrogen bonds. Allowed pairs: G–C, A–U, G–U.
- **Analogy:** A mated connector pair. Only matching plugs and sockets fit.
- **Where it appears:** The target structures our model is conditioned on (Phase 5) and the folding oracle's output (Phase 3).
- **First explained:** session 01.

### Watson–Crick pairs (canonical pairs)
- **Definition:** The two "standard" pairs: G–C (3 hydrogen bonds, strongest) and A–U (2 hydrogen bonds).
- **Analogy:** A 3-pin keyed connector (G–C) and a 2-pin one (A–U). The 3-pin one grips harder.
- **Where it appears:** Pairing rules inside folding software (ViennaRNA).
- **First explained:** session 01.

### Wobble pair (G–U)
- **Definition:** A weaker, slightly misaligned pair between G and U that RNA allows.
- **Analogy:** A connector that fits but a little loosely.
- **Where it appears:** Pairing rules inside folding software.
- **First explained:** session 01.

### Complementary
- **Definition:** Two stretches of sequence are complementary if their bases can pair position by position when lined up in opposite directions.
- **Analogy:** A plug and a socket strip whose pins all match.
- **Where it appears:** Not yet in code.
- **First explained:** session 01.

### Stacking
- **Definition:** Consecutive base pairs sit flat on top of each other like a stack of coins, and this stacking is what actually stabilises them. A lone pair is unstable.
- **Analogy:** One Velcro hook doesn't hold; a strip of hooks does.
- **Where it appears:** The energy model used by folding software (session 01, concept 4).
- **First explained:** session 01.

### Antiparallel
- **Definition:** When RNA folds back on itself, the two paired stretches run in opposite directions, so the first base pairs with the last, the second with the second-to-last, and so on.
- **Analogy:** Folding a strip of paper in half: the two ends meet.
- **Where it appears:** Dot-bracket notation (concept 3).
- **First explained:** session 01.

### Hairpin (stem-loop)
- **Definition:** The simplest RNA fold: a stretch pairs with a later stretch, making a paired "stem" capped by an unpaired "loop" at the turn.
- **Analogy:** A hairpin, literally: two parallel arms joined by a bend.
- **Where it appears:** Everywhere in RNA structures. Detailed in concept 3.
- **First explained:** session 01.

### Minimum hairpin loop size
- **Definition:** The turn of a hairpin must contain at least 3 unpaired bases, because the backbone cannot bend more tightly.
- **Analogy:** The minimum bend radius of a cable or PCB trace.
- **Where it appears:** A hard rule in folding software.
- **First explained:** session 01.

### Primary / secondary / tertiary structure
- **Definition:** Primary = the sequence of bases. Secondary = which bases are paired with which. Tertiary = the actual 3D shape in space.
- **Analogy:** Component list → netlist/schematic (what connects to what) → physical layout (where everything sits in space).
- **Where it appears:** We model primary (the output) and secondary (the target). Tertiary is out of scope.
- **First explained:** session 01.

### Stem (helix)
- **Definition:** A run of consecutive stacked base pairs.
- **Analogy:** A strip of Velcro, or a ladder whose rungs are the pairs.
- **Where it appears:** Runs of `(((` … `)))` in dot-bracket.
- **First explained:** session 01.

### Hairpin loop
- **Definition:** The unpaired bases at the tip of a hairpin, closed by one pair. Minimum 3 bases.
- **Analogy:** The bend of a hairpin.
- **Where it appears:** `(...)` patterns in dot-bracket.
- **First explained:** session 01.

### Bulge
- **Definition:** Unpaired bases on only one side of a stem, interrupting it.
- **Analogy:** A kink on one wire of a twisted pair.
- **Where it appears:** e.g. `((.((...))))`.
- **First explained:** session 01.

### Internal loop
- **Definition:** Unpaired bases on both sides of a stem, interrupting it.
- **Analogy:** A small gap in the middle of a zip, on both sides.
- **Where it appears:** e.g. `((..((...))..))`.
- **First explained:** session 01.

### Multiloop (junction)
- **Definition:** A loop from which three or more stems branch out.
- **Analogy:** A junction box where several cables meet.
- **Where it appears:** e.g. `((..(((...)))..(((...)))..))`.
- **First explained:** session 01.

### Pseudoknot
- **Definition:** Two base pairs that cross: (i, j) and (k, l) with i < k < j < l. Real, but excluded by standard secondary-structure tools and by this project.
- **Analogy:** Two wires that must cross on a single-layer board with no via.
- **Where it appears:** A known limitation of our evaluation (to be recorded in STUDY_GUIDE Part 9).
- **First explained:** session 01.

### Dot-bracket notation
- **Definition:** A string as long as the sequence, where `(` pairs with a later matching `)`, and `.` is unpaired.
- **Analogy:** Balanced parentheses in code.
- **Where it appears:** ViennaRNA's output format; the structure targets our model is conditioned on (Phase 5).
- **First explained:** session 01.

### Folding (the forward problem)
- **Definition:** Predicting which structure a given sequence adopts: sequence → structure.
- **Analogy:** Simulation. Given a circuit, compute what it does.
- **Where it appears:** Our evaluation oracle (Phase 3) folds every generated sequence.
- **First explained:** session 01.

### Free energy (ΔG)
- **Definition:** A single number scoring how stable a structure is, relative to the unfolded chain (which is 0). More negative = more stable. Defined as ΔG = ΔH − T·ΔS, where ΔH is the energy released by forming bonds (negative = favourable), T is absolute temperature in kelvin (body ≈ 310 K), and ΔS is the change in the chain's freedom of movement (folding reduces freedom, so ΔS < 0 and −T·ΔS is a positive cost).
- **Analogy:** The height of a valley in a landscape. A ball (the molecule) settles in low valleys while the ground shakes (thermal noise).
- **Where it appears:** ViennaRNA's output; MFE distributions in our evaluation (Phase 3).
- **First explained:** session 01.

### Enthalpy (ΔH) and entropy (ΔS)
- **Definition:** The two ingredients of free energy. Enthalpy is the energy gained from forming bonds (pairs, stacks). Entropy is the amount of freedom (number of possible arrangements) the molecule has; losing it is a cost that grows with temperature.
- **Analogy:** Enthalpy = the glue pulling a formation together; entropy = everyone's urge to wander off. Heat makes the urge stronger.
- **Where it appears:** Only inside the energy model. We never compute them directly.
- **First explained:** session 01.

### kcal/mol
- **Definition:** The unit of free energy used in RNA folding: kilocalories per mole, where a mole is a fixed, very large count of molecules (6 × 10²³). In practice only *differences* matter. Thermal noise at body temperature is worth ≈ 0.6 kcal/mol.
- **Analogy:** Volts on a logic rail: the absolute number matters less than the margin between levels.
- **Where it appears:** Every energy number in this project.
- **First explained:** session 01.

### Nearest-neighbour energy model
- **Definition:** A way to compute a structure's ΔG by adding up local pieces: each stack of two adjacent pairs contributes a (negative) bonus, each loop a (mostly positive) penalty, looked up from experimentally measured tables.
- **Analogy:** Estimating a chip's power by summing per-block contributions from a characterised cell library.
- **Where it appears:** Inside ViennaRNA (our folding oracle).
- **First explained:** session 01.

### Turner parameters
- **Definition:** The standard tables of experimentally measured energy values (stacks, loops, etc.) used by the nearest-neighbour model, named after the chemist Douglas Turner.
- **Analogy:** A standard-cell library's characterisation data (.lib files).
- **Where it appears:** ViennaRNA's default energy parameters.
- **First explained:** session 01.

### Minimum free energy (MFE) / MFE structure
- **Definition:** The MFE structure is the valid secondary structure with the lowest total ΔG for a given sequence; the MFE is that ΔG value. It is the model's best guess at the structure the RNA adopts.
- **Analogy:** The lowest valley in the landscape.
- **Where it appears:** Our designability metric checks whether a generated sequence's MFE structure equals the target (Phase 3).
- **First explained:** session 01.

### Energy gap (margin)
- **Definition:** How much lower the best structure's energy is than the next-best rival's. Rule of thumb: every ≈1.4 kcal/mol of gap means ≈10× more time spent in the better structure.
- **Analogy:** The noise margin of a logic gate. If the margin is smaller than the noise, the output flips.
- **Where it appears:** A likely extra evaluation criterion (Phase 3).
- **First explained:** session 01.

### Zuker algorithm
- **Definition:** The classic dynamic-programming algorithm that finds the MFE structure in O(N³) time. It relies on the no-crossing rule so that each sub-stretch can be solved independently.
- **Analogy:** Static timing analysis, which never lists every path but reuses per-node results.
- **Where it appears:** The core of ViennaRNA's `RNAfold`.
- **First explained:** session 01.

### Boltzmann distribution
- **Definition:** The physics rule for how a molecule divides its time among possible structures: probability ∝ e^(−ΔG/RT), where R is the gas constant (0.001987 kcal/(mol·K), a unit converter from temperature to energy), T is the temperature in kelvin, and RT ≈ 0.616 kcal/mol at 37 °C is the thermal noise level. For two structures, the time ratio is e^(gap/RT) = 10^(gap/1.42): every ≈1.42 kcal/mol of gap is a 10× preference.
- **Analogy:** MOSFET subthreshold swing (≈60 mV/decade at room temperature). The same physics, thermal energy × ln 10 per decade.
- **Where it appears:** Energy-gap reasoning; ensemble-based metrics (Phase 3).
- **First explained:** session 01.

### Mutation
- **Definition:** A change of one letter (base) in a sequence, e.g. `GGGAAACCC` → `GGGAAACCA`.
- **Analogy:** A single bit flip.
- **Where it appears:** Local-search design methods; later, sequence-editing ideas in Phase 5.
- **First explained:** session 01.

### Inverse folding (RNA design)
- **Definition:** Finding a sequence whose MFE structure is a given target: structure → sequence. This is the problem our project attacks.
- **Analogy:** Synthesis. Given a spec, find a circuit that meets it.
- **Where it appears:** The whole project; conditional generation in Phase 5.
- **First explained:** session 01.

### Designability (preview)
- **Definition:** The fraction of generated sequences that actually fold (according to the oracle) into their intended target structure.
- **Analogy:** Yield: the fraction of manufactured chips that pass test.
- **Where it appears:** A headline metric in Phase 3. Defined precisely there.
- **First explained:** session 01 (preview only).

---

## Machine learning

### Generative model
- **Definition:** A model that learns the distribution of its training data (which sequences are likely and which aren't), so you can draw new, different samples from it.
- **Analogy:** An experienced designer who has seen thousands of circuits and can propose plausible new ones on demand, versus a random-netlist generator.
- **Where it appears:** The whole project: RiboMamba is a generative model of RNA sequences.
- **First explained:** session 01 (intuition only; formal treatment in Phase 2).

### Oracle
- **Definition:** A trusted external checker used to score the model's outputs. For us it is folding software, which predicts each generated sequence's structure.
- **Analogy:** The golden reference model in verification: the testbench compares the design under test against it.
- **Where it appears:** The evaluation harness (Phase 3).
- **First explained:** session 01.

---

## Maths

### Search space
- **Definition:** The set of all candidate solutions. For RNA of length N it contains 4^N sequences (N = 50 → about 1.3 × 10³⁰).
- **Analogy:** Every possible truth table for a circuit with many inputs: exhaustive testing is impossible.
- **Where it appears:** Why we generate rather than search (STUDY_GUIDE Part 2).
- **First explained:** session 01.

### Big-O notation (e.g. O(N³))
- **Definition:** A way of saying how a computation's cost grows with input size N, ignoring constant factors. O(N³) means doubling N makes it about 8× slower.
- **Analogy:** How a circuit's area scales with bit-width (a ripple-carry adder is O(N); an array multiplier is O(N²)).
- **Where it appears:** Folding cost (O(N³)); later, Transformer attention O(N²) vs Mamba O(N) in Phase 4.
- **First explained:** session 01.

### Dynamic programming
- **Definition:** Solving a big problem by splitting it into smaller overlapping sub-problems, solving each once, storing the answer, and reusing it.
- **Analogy:** Static timing analysis computes the worst arrival time at each node once and reuses it, instead of enumerating exponentially many paths.
- **Where it appears:** Inside the folding software (Zuker algorithm).
- **First explained:** session 01.

### Local search and local minima
- **Definition:** Local search improves a solution by small changes (e.g. mutate one letter, keep it if better). A local minimum is a point where every small change makes things worse, even though a better solution exists elsewhere.
- **Analogy:** A ball stuck in a small dip on a hillside, unable to reach the deep valley beyond the next ridge.
- **Where it appears:** Why classical design tools (e.g. RNAinverse) struggle; the contrast that motivates generative models.
- **First explained:** session 01.

### Simulated annealing
- **Definition:** A local-search variant that sometimes accepts a *worse* step on purpose, more often early on and less often later, so it can climb out of local minima.
- **Analogy:** Annealing metal (or annealing in wafer processing): heat it so atoms can escape bad arrangements, then cool slowly so they settle into a good one.
- **Where it appears:** Mentioned only as a patch that classical design tools use.
- **First explained:** session 01.

---

## Software

### Operating system (OS)
- **Definition:** The base software that sits between programs and the hardware. It decides which program gets the CPU when, hands out memory, manages files on disk, and talks to devices such as the GPU. Windows and Linux are two different operating systems.
- **Analogy:** A bus arbiter plus memory controller on a chip. Many masters (programs) want shared resources (CPU, RAM, disk), and one controller keeps them from trampling each other.
- **Where it appears:** We develop on Linux (inside WSL2) running on a Windows machine.
- **First explained:** session 02.

### Kernel
- **Definition:** The core of an operating system: the part that directly controls the hardware. Everything else (the terminal, the tools) is ordinary programs asking the kernel for services.
- **Analogy:** The firmware/microcode layer of a processor. Programs never touch the silicon directly; they go through it.
- **Where it appears:** WSL2 runs a real Linux kernel (WSL1 did not).
- **First explained:** session 02.

### Linux, and Linux distribution ("distro")
- **Definition:** Linux is a free operating system (strictly, a kernel) that almost all scientific computing, servers and cloud GPUs run on. A distribution packages the Linux kernel with a standard set of tools and a package manager. Ubuntu is one popular distribution.
- **Analogy:** The kernel is the processor core; a distribution is a complete dev board built around it, with peripherals and a toolchain already fitted.
- **Where it appears:** Our environment is Ubuntu, running in WSL2.
- **First explained:** session 02.

### Virtual machine (VM) and hypervisor
- **Definition:** A virtual machine is a complete computer simulated in software, with its own OS, running on real hardware alongside the main OS. The hypervisor is the layer that shares out the real CPU, memory and devices so each OS believes it owns the machine.
- **Analogy:** Partitioning one chip so two independent systems share the silicon, with an arbiter giving each the illusion of exclusive access.
- **Where it appears:** WSL2 is a lightweight VM managed by Windows.
- **First explained:** session 02.

### WSL2 (Windows Subsystem for Linux, version 2)
- **Definition:** A Microsoft feature that runs a real Linux kernel inside a lightweight, tightly integrated virtual machine, so Linux tools run on a Windows PC without rebooting. It can also use the NVIDIA GPU through the Windows driver ("GPU passthrough").
- **Analogy:** A second, fully independent processor on the same board running different firmware, with a bridge that lets both see each other's files and share the GPU.
- **Where it appears:** Our whole development environment. Checked with `wsl --status` and `wsl --list --verbose` in session 02 (already installed: Ubuntu, version 2).
- **First explained:** session 02.

### WSL1 vs WSL2
- **Definition:** WSL1 had no Linux kernel. It translated each Linux request into an equivalent Windows request on the fly. WSL2 runs a genuine Linux kernel, so it is fully compatible and much faster on Linux-side files, but slower when reaching into Windows files.
- **Analogy:** WSL1 is a protocol translator (converts every packet); WSL2 is a native second device with a bridge between them.
- **Where it appears:** Our machine uses WSL2 (the `VERSION 2` column).
- **First explained:** session 02.

### Terminal, shell, PowerShell, bash
- **Definition:** A terminal is the text window. A shell is the program inside it that reads a typed command, runs it and prints the result. PowerShell is the Windows shell; bash is the standard Linux shell. They use different command syntax.
- **Analogy:** A shell is a command interpreter like a JTAG console or UART monitor: you type an instruction, it executes it on the device and replies.
- **Where it appears:** Every command in the logbook says which shell it ran in.
- **First explained:** session 02.

### Character encoding (UTF-8, UTF-16)
- **Definition:** The rule for turning text characters into bytes. UTF-16 uses 2 bytes per plain English letter (the second one is 0x00); UTF-8 uses 1. Decoding with the wrong rule gives garbled text.
- **Analogy:** Reading a 16-bit bus as if it were 8 bits wide: every other byte you see is a meaningless zero.
- **Where it appears:** Why `wsl --status` printed `D e f a u l t` with gaps in session 02.
- **First explained:** session 02.

### Virtual disk (`.vhdx`) and file system (ext4)
- **Definition:** A virtual disk is one ordinary Windows file that contains an entire disk drive inside it. WSL2 keeps each Linux distro's whole disk in a file called `ext4.vhdx`. ext4 is the file-system format Linux uses inside it, meaning the rules for how files and folders are laid out on a disk.
- **Analogy:** An SD-card image for a Raspberry Pi, or a ROM image loaded into an emulator: one file that *is* a whole drive.
- **Where it appears:** Session 02: Ubuntu wouldn't start because its `ext4.vhdx` had been deleted.
- **First explained:** session 02.

### Windows registry
- **Definition:** Windows' central database of settings. WSL stores its list of installed distros there, including where each one's disk file lives.
- **Analogy:** A configuration register map, or a phone book. It says where something *should* be, not whether it's still there.
- **Where it appears:** Session 02 diagnosis: the registry still listed Ubuntu after its disk was deleted.
- **First explained:** session 02.

### Dangling reference (dangling pointer)
- **Definition:** A reference that still exists after the thing it points to has been deleted. Using it fails.
- **Analogy:** A netlist that instantiates a cell whose layout file has been deleted, or a C pointer to freed memory.
- **Where it appears:** Session 02: the broken Ubuntu registration.
- **First explained:** session 02.

### LTS (Long-Term Support)
- **Definition:** A software release that gets security and bug fixes for several years (Ubuntu LTS: 5 years standard). Preferred when you want a stable, reproducible base rather than the newest features.
- **Analogy:** A mature, fully characterised process node versus a brand-new one: fewer surprises, better tool support.
- **Where it appears:** We plan to install Ubuntu 24.04 LTS.
- **First explained:** session 02.

### root, user accounts, and sudo
- **Definition:** Linux has one all-powerful administrator account, `root`, and ordinary user accounts that can only change their own files. `sudo` ("superuser do") lets an ordinary user run a single command as root, after typing their password.
- **Analogy:** Normal operation versus test mode with write access to fuses. You want the dangerous mode only for the one command that needs it.
- **Where it appears:** Our Linux user is `chirag` (member of the `sudo` group). Setup commands in session 02 ran as `root` via `wsl -u root`.
- **First explained:** session 02.

### `/mnt/c` (mount point)
- **Definition:** The folder through which Linux inside WSL sees the Windows C: drive. `C:\Users\chira\...` appears as `/mnt/c/Users/chira/...`. Every access through it crosses the Windows↔Linux bridge.
- **Analogy:** A window in the address map that points off-chip, through a bus bridge.
- **Where it appears:** Session 02: a WSL shell started in `/mnt/c/Users/chira/OneDrive/Desktop/RiboMamba`, the reason for decision D-002.
- **First explained:** session 02.

### GPU driver, `nvidia-smi`, "CUDA Version"
- **Definition:** The driver is the software that lets the OS talk to the GPU. `nvidia-smi` is NVIDIA's status tool: it shows the GPU model, memory and running jobs. Its "CUDA Version" is the *newest* CUDA the driver supports, not an installed toolkit. CUDA itself (NVIDIA's GPU programming platform) is explained properly when PyTorch is installed.
- **Analogy:** The driver is the device's firmware interface; `nvidia-smi` is its status register dump.
- **Where it appears:** Session 02: RTX 4060 Laptop, 8188 MiB (8 GB) VRAM, driver 595.79, CUDA ≤ 13.2, visible from inside WSL.
- **First explained:** session 02.

### Git, repository, commit
- **Definition:** Git is a version-control system: it records snapshots of your project over time. The repository is the project folder plus Git's hidden database (`.git/`). A commit is one saved snapshot, with an author, a time and a message explaining why it was made.
- **Analogy:** Tape-out revisions with a change log. Every revision is kept, and you can always return to any earlier one.
- **Where it appears:** `~/projects/RiboMamba` is a Git repository. First commit `f495772`, session 02.
- **First explained:** session 02.

### Staging area (`git add`)
- **Definition:** The waiting room between editing files and committing them. `git add` puts chosen changes in it; `git commit` turns exactly those into a snapshot.
- **Analogy:** Choosing which modified cells go into this revision before signing it off.
- **Where it appears:** Every commit.
- **First explained:** session 02.

### Commit hash
- **Definition:** A 40-hex-digit fingerprint that identifies a commit, calculated from its contents and its parent commit. Change anything in history and every later hash changes, so tampering is visible. Usually shortened to the first 7 digits (e.g. `f495772`).
- **Analogy:** A CRC/checksum over the whole history chain.
- **Where it appears:** RESULTS.md records the commit hash next to every number, for reproducibility.
- **First explained:** session 02.

### Branch (`main`)
- **Definition:** A named line of commits. A new repository starts with one; we call it `main`.
- **Analogy:** A named design revision track.
- **Where it appears:** Our only branch so far.
- **First explained:** session 02 (briefly; more when we need a second branch).

### Remote, push, GitHub
- **Definition:** A remote is another copy of the repository, somewhere else. GitHub is a website that hosts remotes. `git push` sends your new commits to the remote.
- **Analogy:** An off-site backup of the design database, updated whenever you choose.
- **Where it appears:** `Chikap1009/RiboMamba` on GitHub (public). Pushed at the end of every session (D-002).
- **First explained:** session 02.

### `gh` (GitHub CLI)
- **Definition:** GitHub's command-line tool. It logs you in to GitHub and can create repositories, among other things, without opening the website.
- **Analogy:** A command-line interface to a web service, instead of clicking through its GUI.
- **Where it appears:** Installed in Ubuntu (version 2.45.0), session 02.
- **First explained:** session 02.

### Noreply email
- **Definition:** A private address GitHub gives each user (`ID+username@users.noreply.github.com`). Commits made with it are linked to your profile without exposing your real email in a public repository.
- **Analogy:** A PO box instead of your home address.
- **Where it appears:** Our Git author email.
- **First explained:** session 02.

### apt (package manager)
- **Definition:** Ubuntu's tool for installing system software from Ubuntu's official collection. `apt-get update` refreshes the catalogue; `apt-get install X` installs X. It needs root.
- **Analogy:** An app store for the command line.
- **Where it appears:** Installed `gh` in session 02. (Python packages will come from conda instead, explained at step 4.)
- **First explained:** session 02.

### Shell script
- **Definition:** A text file containing shell commands, run in order with `bash file.sh`. We use them to avoid typing long Linux commands through PowerShell, which rewrites quotes and `$` signs.
- **Analogy:** A test vector file you replay, instead of typing every stimulus by hand.
- **Where it appears:** One-off setup scripts in session 02 (kept outside the repo).
- **First explained:** session 02.

### Time zone vs. clock
- **Definition:** A computer's clock counts one universal time (UTC). The time zone only controls how that time is *displayed* (IST = UTC + 5:30).
- **Analogy:** The same voltage shown on two meters with different offsets.
- **Where it appears:** Ubuntu was showing UTC; set to Asia/Kolkata in session 02. Git records the offset with every commit.
- **First explained:** session 02.

### Bioconda (preview)
- **Definition:** A community collection of ready-to-install bioinformatics software packages (ViennaRNA is one), distributed through conda. It builds packages for Linux and macOS only, not Windows.
- **Analogy:** A vendor's IP catalogue that only ships for certain process nodes.
- **Where it appears:** How we will install ViennaRNA (step 5). Conda itself is explained at step 4.
- **First explained:** session 02 (preview).

### Stack (data structure)
- **Definition:** A list where you can only add to the top (push) or remove from the top (pop): last in, first out.
- **Analogy:** A stack of plates, or a hardware return-address stack.
- **Where it appears:** Decoding dot-bracket into base pairs.
- **First explained:** session 01.
