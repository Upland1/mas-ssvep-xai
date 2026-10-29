# Pipeline entry points (P24: `make all` regenerates every CSV from the raw recordings).
#
#   make all                  every phase target p00 ... p23, in order, resumable (see below)
#   make p14                  one phase
#   make -n all               list every command without running anything
#   make loso-all             optional, outside `all`: P21 39-subject classical LOSO + within reference
#   make help                 this list
#
# Variables (override on the command line or in the environment):
#   PYTHON   interpreter                          (default .venv/bin/python)
#   RAW_DIR  folder with the S<nn>/ recordings    (default data/raw); passed as --raw-dir to every script that reads recordings
#   NN_DEVICES  devices of the P08 EEGNet run     (default "cpu"; "cpu cuda" also runs the CUDA row)
#   FORCE=1  rerun phases that `make all` already finished
#   STAMPS   folder of the per-phase "done" stamps (default mas/state/scratch/make_stamps)
#
# Every target is a recorded phase run (mas/state/phases/Pxx-*/05_run.md and the "Run commands" of 02_plan.md),
# with --subjects S01 ... S05 wherever a script would otherwise discover subjects (the raw folder may hold more).
# Targets write to the same out-dirs as the phase runs and can be repeated. Targets do not depend on one another:
# `make all` is what orders them (later phases read the outputs of earlier ones).
# `make all` writes $(STAMPS)/<target>.done (elapsed seconds) after each finished phase and skips it next time,
# so an interrupted `make all` resumes at the phase that was running (inside a phase the long jobs resume by
# themselves: build_windows --resume, benchmark_loso and benchmark_gnn_loso skip finished folds).

PYTHON ?= .venv/bin/python
RAW_DIR ?= data/raw
NN_DEVICES ?= cpu
SCRATCH ?= mas/state/scratch
STAMPS ?= $(SCRATCH)/make_stamps

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.NOTPARALLEL:

PHASES := p00 p01 p02 p03 p04 p05 p06 p07 p08 p09 p10 p11 p12 p13 p14 p15 p16 p17 p18 p19 p20 p21 p22 p23
DRY := $(findstring n,$(firstword $(filter-out --%,-$(MAKEFLAGS))))

define NL


endef

P := $(PYTHON) -m
SUBJ := S01 S02 S03 S04 S05
S := --subjects $(SUBJ)
RAW := --raw-dir $(RAW_DIR)

FB := scripts.benchmarks.feature_based
NNB := scripts.benchmarks.neural_networks
CONN := scripts.connectivity
CC := $(P) $(CONN).analysis.analyze_connectivity_cohort
PW := $(P) $(CONN).comparison.test_connectivity_frequency_differences
NSUB := $(P) $(FB).benchmark_n_subjects
BUILD := $(P) scripts.build_windows
LOSO := $(P) scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25
GNNL := $(P) $(CONN).graph_modeling.benchmark_gnn_loso

COH4 := --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1
BANKS4 := --banks fbcca fbcsp harmonic intermediate
SWEEP_W := 0.5 1 1.5 2 3 4

.PHONY: help venv test all all-dry loso-all inventory preprocess explore $(PHASES)

help:
	@echo "make all        every phase target p00 ... p23 in order (resumable; FORCE=1 reruns finished phases)"
	@echo "make pNN        one phase (p00 ... p23); make -n pNN lists its commands"
	@echo "make loso-all   optional, outside all: P21 classical LOSO and within reference on every built subject"
	@echo "make test       run the synthetic test suite (no real data)"
	@echo "make venv       create .venv and install requirements.txt"
	@echo "variables: PYTHON ($(PYTHON)), RAW_DIR ($(RAW_DIR)), NN_DEVICES ($(NN_DEVICES)), STAMPS ($(STAMPS))"

venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

test:
	$(PYTHON) -m pytest tests/ -q

all-dry:
	@$(MAKE) --no-print-directory -n all

all:
	@set -e; for p in $(PHASES); do \
	  if [ -z "$(DRY)" ] && [ -z "$(FORCE)" ] && [ -f $(STAMPS)/$$p.done ]; then \
	    echo "[skip] $$p already done ($(STAMPS)/$$p.done); FORCE=1 reruns it"; continue; fi; \
	  echo "=== $$p $$(date +%Y-%m-%dT%H:%M:%S)"; t0=$$(date +%s); \
	  $(MAKE) --no-print-directory $$p; \
	  if [ -z "$(DRY)" ]; then mkdir -p $(STAMPS); echo "$$(( $$(date +%s) - t0 )) s" > $(STAMPS)/$$p.done; fi; \
	done

# Short names kept from the earlier phases.
inventory: p00
explore: p03

# make preprocess: P02 legacy 7-channel windows + PSD (--legacy-p02) -> data/processed/<S>/ (same command as p02;
# --legacy-p02 reproduces the P02 arrays after the P07 two-tier gate became the default).
preprocess:
	$(P) scripts.preprocessing.run_preprocessing $(S) --legacy-p02 $(RAW)

# ---------------------------------------------------------------- Era A (legacy windows, leaky CV)

# P00 header and MARK inventory of the recordings.
p00:
	$(P) scripts.exploration.inventory_raw $(S) $(RAW)

# P01 the parser inventory must equal the P00 one (cmp prints nothing); then the strict variant.
p01:
	mkdir -p reports/P01
	$(P) scripts.exploration.inventory_raw $(S) $(RAW) --out reports/P01/raw_inventory_parser.csv
	cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser.csv
	$(P) scripts.exploration.inventory_raw $(S) $(RAW) --strict --out reports/P01/raw_inventory_parser_strict.csv

# P02 legacy 7-channel windows and PSD -> data/processed/<S>/ (P02 itself ran `--all`; see `preprocess` above).
p02: preprocess

# P03 occipital spectra and PSD by class, legacy fs 250 and header fs 256.
p03:
	$(P) scripts.exploration.diagnose_occipital_spectra $(S)
	$(P) scripts.exploration.diagnose_occipital_spectra $(S) --fs 256 --out-suffix header
	$(P) scripts.exploration.visualize_data $(S)
	$(P) scripts.exploration.visualize_data $(S) --fs 256 --out-suffix header

# P04 early models and XAI (the recorded `train_models --all` is one call per subject here, same outputs).
p04:
	$(foreach s,$(SUBJ),$(P) scripts.training.train_models --subject $(s)$(NL))
	$(P) scripts.training.train_final_model --subject S01 --device cpu
	$(P) scripts.training.train_final_model --subject S04 --device cpu
	$(P) scripts.training.batch_run_subjects $(S) --device cpu $(RAW)
	$(P) scripts.xai.run_xai --subject S04
	$(P) scripts.xai.compare_subject_xai

# P05 feature-space benchmark and confusion matrices.
p05:
	$(P) $(FB).benchmark_cross_validation --subject S03 --cv legacy --smoothing mod5
	$(P) $(FB).benchmark_harmonic_fbcca --subject S03 --cv legacy --smoothing mod5
	$(P) scripts.evaluation.test_sklearn_models --subject S03
	$(P) scripts.evaluation.evaluate_confusion_matrix --subject S03 --cv legacy --smoothing mod5
	$(P) scripts.evaluation.evaluate_confusion_matrix --subject S03 --m 2 --cv legacy --smoothing mod5
	$(foreach s,S01 S02 S04 S05,$(P) scripts.evaluation.evaluate_confusion_matrix --subject $(s) --cv legacy --smoothing mod5$(NL))
	$(P) scripts.exploration.visualize_data --subject S03

# P06 feature selection (S03) and the five-subject benchmark; the last line is the recorded SFS diagnostic.
p06:
	$(P) $(FB).benchmark_feature_selection --subject S03 --k-features 20 --cv legacy --smoothing mod5
	$(P) $(FB).benchmark_5_subjects $(S)
	$(P) $(FB).benchmark_feature_selection --subject S03 --k-features 20 --cv legacy --smoothing mod5 --sfs-diagnostics --n-jobs 8

# Era A (P05-P10) commands pass --cv legacy --smoothing mod5: since P11 the default is trial-grouped CV and the leaky
# outputs go to reports/legacy_leaky/. Builds of P16/P17 pass --quality-source filtered --banks (config default since P19: both).
# P07 PF-07 regression demos (vpp_min 5.0; the second run exits 1 by design: S03 has no accepted window) and the cohort table.
p07:
	$(P) scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --processed-dir data/processed_p07_demo/vppmin5 --no-figures $(RAW)
	-$(P) scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --no-channel-drop --processed-dir data/processed_p07_demo/vppmin5_nodrop --no-figures $(RAW)
	$(P) scripts.preprocessing.run_preprocessing --subject S03 --processed-dir data/processed_p07_demo/pinned --no-figures $(RAW)
	$(NSUB) $(S) --data-root data/processed --n-jobs 5 --cv legacy --smoothing mod5

# P08 EEGNet on S03, legacy leaky CV (NN_DEVICES: cpu, and cuda when a GPU is present).
p08:
	$(foreach d,$(NN_DEVICES),$(P) $(NNB).benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device $(d) --augment off --cv legacy --smoothing mod5$(NL))

# P09 Compact-CNN and ShallowConvNet on S03, parameter counts.
p09:
	$(P) $(NNB).count_parameters
	$(P) $(NNB).benchmark_compact_cnn --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off --cv legacy --smoothing mod5
	$(P) $(NNB).benchmark_shallow_convnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off --cv legacy --smoothing mod5

# P10 augmentation A/B, legacy leaky CV (also writes reports/legacy_leaky/).
p10:
	$(foreach m,eegnet compact_cnn shallow_conv_net,$(P) $(NNB).benchmark_nn_augmentation $(S) --model $(m) --epochs 150 --device cpu --cv legacy --smoothing mod5 --freeze-legacy$(NL))

# ---------------------------------------------------------------- Era B (trial-grouped CV, connectivity)

# P11 trial-leakage fix: legacy snapshot, then the leak-free reruns, leakage demo before and after the A/B.
p11:
	$(NSUB) $(S) --cv legacy --smoothing mod5
	$(P) $(FB).benchmark_cross_validation --subject S03 --cv legacy --smoothing mod5
	$(P) $(FB).benchmark_feature_selection --subject S03 --k-features 20 --cv legacy --smoothing mod5
	$(P) scripts.diagnostics.demo_cv_leakage $(S)
	$(NSUB) $(S)
	$(P) $(FB).benchmark_cross_validation --subject S03
	$(P) $(FB).benchmark_feature_selection --subject S03 --k-features 20
	$(foreach m,eegnet compact_cnn shallow_conv_net,$(P) $(NNB).benchmark_nn_augmentation $(S) --model $(m) --epochs 150 --device cpu$(NL))
	$(P) scripts.diagnostics.demo_cv_leakage $(S)

# P12 coherence bias demo and per-subject coherence.
p12:
	$(P) $(CONN).diagnostics.demo_coherence_bias --subjects S03 S04
	$(P) $(CONN).analysis.analyze_connectivity --subject S03 --method coherence
	$(P) $(CONN).analysis.analyze_connectivity --subject S04 --method coherence

# P13 phase / PDC / permutation unit: demos, window-level 200, trial-level 100 and 200 (final), comparisons,
# aligned coherence on S03, and the six-seed S05 wPLI diagnostic of the verifier.
p13:
	$(P) $(CONN).diagnostics.demo_hilbert_edges
	$(P) $(CONN).diagnostics.demo_mvar_slicing
	$(CC) $(S) --methods coherence plv wpli pdc --permutations 200 --permutation-unit window --n-jobs -1 --out-suffix window200
	$(CC) $(S) --methods coherence plv wpli pdc --permutations 100 --permutation-unit trial --n-jobs -1 --out-suffix trial100
	$(CC) $(S) --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1
	$(P) $(CONN).analysis.analyze_connectivity_cohort --compare trial100 ""
	$(P) $(CONN).analysis.analyze_connectivity_cohort --compare window200 ""
	$(CC) --methods coherence --subjects S03 --permutations 200 --permutation-unit trial --coherence-estimator aligned --n-jobs -1 --out-suffix aligned_S03
	$(foreach b,42 1 2 3 4 5,$(CC) --methods wpli --subjects S05 --permutations 200 --permutation-unit trial --n-jobs -1 --random-state $(b) --out-suffix diagA2_rs$(b)$(NL))

# P14 cross-frequency comparison, pairwise tests (500 then 1000 permutations), power-alpha confound.
p14:
	$(P) $(CONN).comparison.compare_connectivity_frequencies $(S)
	$(PW) $(S) --permutations 500 --n-jobs -1 --out-suffix p500
	$(PW) $(S) --permutations 1000 --n-jobs -1
	$(PW) --compare p500 ""
	$(P) $(CONN).diagnostics.check_power_alpha_confound $(S)

# P15 graph dataset, connectivity gate, GNN smoke test and benchmark.
p15:
	$(P) $(CONN).graph_modeling.build_graph_dataset $(S) --rebuild
	$(P) $(CONN).graph_modeling.benchmark_connectivity_gate $(S) --repeats 5 --k-select 0 30
	$(P) $(CONN).graph_modeling.benchmark_gnn --smoke-test
	$(P) $(CONN).graph_modeling.benchmark_gnn $(S) --repeats 3 --epochs 150 --device cpu

# ---------------------------------------------------------------- Era C (built folders, continuous filtering)

# P16 freeze the Era A/B outputs (once; a tag is frozen only once), edge-effect demo, builds, regression and v1/v2 rows.
# The regression check exits 0 in the final P16 run, so a failure stops make.
p16:
	ls -d baselines/v1_* > /dev/null 2>&1 || $(P) scripts.freeze_baseline --tag v1 --configs-git-rev 97a29be --note "Era A/B outputs before P16 (main 97a29be)"
	$(P) scripts.diagnostics.demo_edge_effects --subject S03 $(RAW)
	$(BUILD) --filter-mode per_window $(S) --session OO --banks fbcca fbcsp --quality-source filtered --check-legacy-starts $(RAW)
	$(BUILD) --filter-mode continuous $(S) --session OO --banks fbcca fbcsp --quality-source filtered --check-legacy-starts $(RAW)
	$(NSUB) $(S) --out-suffix v1check
	$(CC) $(S) $(COH4) --out-suffix v1check
	$(NSUB) $(S) --cv-repeats 5 --out-suffix v1rep5
	$(NSUB) $(S) --fs 256 --cv-repeats 5 --out-suffix v1fs256
	$(NSUB) $(S) --fs 256 --smoothing trial --cv-repeats 5 --out-suffix v1fs256trial
	$(NSUB) $(S) --data-root data/processed_per_window --quality shared --cv-repeats 5 --out-suffix v2pw
	$(NSUB) $(S) --data-root data/processed_continuous --quality shared --cv-repeats 5 --out-suffix v2cont
	$(NSUB) $(S) --data-root data/processed_continuous --quality shared-no-guard --cv-repeats 5 --out-suffix v2cont_noguard
	$(CC) $(S) $(COH4) --fs 256 --out-suffix v1fs256
	$(CC) $(S) $(COH4) --data-root data/processed_per_window --quality shared --out-suffix v2pw
	$(CC) $(S) $(COH4) --data-root data/processed_continuous --quality shared --out-suffix v2cont
	$(CC) $(S) $(COH4) --data-root data/processed_continuous --quality shared-no-guard --out-suffix v2cont_noguard
	$(P) scripts.diagnostics.compare_v1_v2 --check-regression
	$(P) scripts.diagnostics.compare_v1_v2

# P17 rest class and filter banks: build the four banks, the base regression check, then the six benchmarks.
p17:
	$(BUILD) --filter-mode continuous $(S) --session OO $(BANKS4) --quality-source filtered --out-root data/processed_continuous_p17 $(RAW)
	$(NSUB) $(S) --data-root data/processed_continuous_p17 --quality shared --cv-repeats 5 --bank base --classes 5 --out-suffix p17_diag_base_5class_rep5
	$(foreach b,base harm harm+mid,$(foreach c,5 6,$(NSUB) $(S) --data-root data/processed_continuous_p17 --quality shared --cv-repeats 10 --bank $(b) --classes $(c) --out-suffix p17_$(subst +,,$(b))_$(c)class$(NL)))

# P18 NBS: cohort 200 and 1000 permutations, flips, pairwise tests with split-half reliability, summary.
p18:
	$(CC) $(S) $(COH4) --data-root data/processed_continuous --quality shared --stats nbs --nbs-thresholds 1.5 2.0 2.5 3.0 --nbs-primary 2.0 --out-suffix p18_nbs_p200
	$(CC) $(S) --methods coherence plv wpli pdc --permutations 1000 --permutation-unit trial --n-jobs -1 --data-root data/processed_continuous --quality shared --stats nbs --nbs-thresholds 1.5 2.0 2.5 3.0 --nbs-primary 2.0 --out-suffix p18_nbs
	$(P) $(CONN).analysis.analyze_connectivity_cohort --compare p18_nbs_p200 p18_nbs
	$(PW) $(S) --methods coherence plv wpli --permutations 1000 --data-root data/processed_continuous --quality shared --benchmark reports/n_subjects_benchmark_v2cont.csv --out-suffix p18_nbs
	$(PW) --summary-only --methods coherence plv wpli --out-suffix p18_nbs --benchmark reports/n_subjects_benchmark_v2cont.csv

# P19 raw-signal quality: the three builds (the filtered regression build goes to the scratch folder), four benchmarks.
p19:
	$(BUILD) --filter-mode continuous $(S) --session OO $(BANKS4) --quality-source filtered --out-root $(SCRATCH)/p19_filtered $(RAW)
	$(BUILD) --filter-mode continuous $(S) --session OO $(BANKS4) --quality-source raw --out-root data/processed_continuous_p19_raw $(RAW)
	$(BUILD) --filter-mode continuous $(S) --session OO $(BANKS4) --quality-source both --out-root data/processed_continuous_p19_both $(RAW)
	$(foreach b,base harm,$(NSUB) $(S) --quality shared --cv-repeats 10 --classes 5 --data-root data/processed_continuous_p17 --bank $(b) --out-suffix p19_filtered_$(b)$(NL)$(NSUB) $(S) --quality shared --cv-repeats 10 --classes 5 --data-root data/processed_continuous_p19_both --bank $(b) --out-suffix p19_both_$(b)$(NL))

# P20 detection and online: window-length builds, classical sweep, NN sweep, dynamic stopping (lda), pseudo-online,
# CNN sweep (six invocations, resumable per cell), dynamic stopping (all methods).
p20:
	$(foreach w,$(SWEEP_W),$(BUILD) --filter-mode continuous $(S) --session OO --banks fbcca fbcsp --quality-source both --window-sec $(w) --stride-sec 0.25 $(RAW)$(NL))
	$(P) scripts.benchmarks.benchmark_window_sweep $(S) --data-root data/processed_continuous --windows $(SWEEP_W) --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep
	$(P) $(NNB).benchmark_nn_sweep $(S) --data-root data/processed_continuous --windows 1 --models ccnn compact eegnet --out-dir reports/nn_sweep
	$(P) scripts.benchmarks.simulate_dynamic_stopping reports/window_sweep/predictions.csv --thresholds 0.5 0.6 0.7 0.8 0.9 0.95 --skip-sec 0.5 --out-dir reports/dynamic_stopping_lda
	$(P) scripts.benchmarks.pseudo_online $(S) --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --tag ccnn_5class --quality-source both $(RAW)
	$(P) scripts.benchmarks.pseudo_online $(S) --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --rest-class --tag ccnn_6class --quality-source both $(RAW)
	$(foreach w,$(SWEEP_W),$(P) scripts.benchmarks.benchmark_window_sweep $(S) --data-root data/processed_continuous --windows $(w) --stride 0.25 --methods cnn --cnn-repeats 1 --out-dir reports/window_sweep$(NL))
	$(P) scripts.benchmarks.simulate_dynamic_stopping reports/window_sweep/predictions.csv --thresholds 0.5 0.6 0.7 0.8 0.9 0.95 --skip-sec 0.5 --out-dir reports/dynamic_stopping

# P21 LOSO on the five-subject cohort: build (resume), classical (common and all channels, CPU only), networks, a
# rerun that must skip every fold, and the two extra network seeds. The 39-subject runs are `make loso-all`.
p21:
	$(BUILD) --filter-mode continuous $(S) --session OO --banks fbcca fbcsp --quality-source both --window-sec 1 --stride-sec 0.25 --resume $(RAW)
	CUDA_VISIBLE_DEVICES= $(LOSO) $(S) --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1_s01-s05
	CUDA_VISIBLE_DEVICES= $(LOSO) $(S) --methods fbcca lda lda_subjnorm --channels all --out-dir reports/loso_w1_s01-s05_all
	$(LOSO) $(S) --methods ccnn compact eegnet --channels common --out-dir reports/loso_w1_s01-s05
	CUDA_VISIBLE_DEVICES= $(LOSO) $(S) --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1_s01-s05
	$(foreach k,43 44,$(LOSO) $(S) --methods ccnn eegnet --channels common --seed $(k) --out-dir reports/loso_w1_s01-s05_seed$(k)$(NL))

# P22 LOSO extensions: matched within-subject LDA, channel sets, warm-up (classical, CPU).
p22:
	$(foreach c,common all,CUDA_VISIBLE_DEVICES= $(LOSO) $(S) --methods fbcca lda lda_subjnorm within_lda --channels $(c) --folds 5 --within-repeats 5 --out-dir reports/loso_w1_p22_$(c)$(NL))
	CUDA_VISIBLE_DEVICES= $(LOSO) $(S) --methods fbcca lda lda_subjnorm within_lda --channels PO7 PO3 POz PO4 PO8 O1 Oz O2 --folds 5 --within-repeats 5 --out-dir reports/loso_w1_p22_names
	$(P) scripts.benchmarks.benchmark_loso_warmup --data-root data/processed_continuous --window 1 --stride-sec 0.25 $(S) --warmup-trials 1 2 5 10 --channels common --out-dir reports/loso_warmup

# P23 GNN under LOSO and its within-subject reference (CPU, 2 threads, 3 seeds, pooled and per-subject normalization).
p23:
	$(GNNL) --smoke-test --out-dir $(SCRATCH)/p23_verify_smoke
	$(GNNL) --data-root data/processed_continuous --window 1 --stride-sec 0.25 $(S) --channels common --variants nodes+F nodes+coh+F --norm pooled --protocol within --seeds 3 --threads 2 --device cpu --out-dir reports/within_gnn
	$(GNNL) --data-root data/processed_continuous --window 1 --stride-sec 0.25 $(S) --channels common --variants nodes+F nodes+coh+F --norm pooled subject --protocol loso --seeds 3 --threads 2 --device cpu --out-dir reports/loso_gnn

# ---------------------------------------------------------------- optional, outside `all`

# P21 human-run part that fits a workstation: classical LOSO and the within reference on EVERY subject folder in
# RAW_DIR (these commands discover subjects on purpose). The 39-subject network LOSO (about 1.5 h GPU) is not included.
loso-all:
	$(BUILD) --filter-mode continuous --session OO --banks fbcca fbcsp --quality-source both --window-sec 1 --stride-sec 0.25 --resume $(RAW)
	$(P) scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows 1 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep_w1_all
	CUDA_VISIBLE_DEVICES= $(LOSO) --methods fbcca --channels all --out-dir reports/loso_w1_fbcca_all
	CUDA_VISIBLE_DEVICES= $(LOSO) --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1
	CUDA_VISIBLE_DEVICES= $(LOSO) --methods fbcca lda lda_subjnorm --channels all --out-dir reports/loso_w1_all
