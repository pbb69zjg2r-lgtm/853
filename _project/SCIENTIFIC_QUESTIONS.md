# Scientific Questions

Updated: 2026-06-26

This file is the human-readable authority for the 7 scientific questions used by `evidence_type`.

The enum names stay stable in code and contracts. The question wording below defines what each enum means and how to resolve overlap.

## Current 7 Questions

| # | evidence_type | Scientific question | Extract when the paper says... | Do not extract when... |
|---|---|---|---|---|
| 1 | `disease_association` | What relationship does a disease or pathological state have with mitochondrial thermogenesis or thermogenic dysfunction? | A disease, patient state, metabolic disorder, or pathological phenotype is directly linked to altered thermogenesis, mitochondrial heat production, BAT/beige fat activity, or thermogenic metabolism. | The text is only general disease background, or only reports a genetic association without a functional thermogenesis / mitochondrial link. |
| 2 | `detection_method` | How is thermogenesis or a thermogenesis-relevant variable measured? | The finding is about a method, assay, sensor, imaging approach, readout, or measurement principle for thermogenesis, mitochondrial activity, heat production, OCR, temperature, BAT activity, or related metabolic output. | A routine method is merely used to support another biological finding, such as Western blot/qPCR/immunofluorescence used only to measure a marker. |
| 3 | `thermogenesis_modulation` | What intervention changes thermogenesis, and in what direction? | A drug, gene manipulation, environmental exposure, diet, temperature treatment, disease model, or other intervention increases, decreases, restores, or suppresses thermogenic output or a clearly thermogenic phenotype. | The claim only describes an internal pathway without an explicit intervention, or only reports marker expression without enough thermogenic output context. |
| 4 | `biomarker_panel` | Which marker combination can judge thermogenic state or thermogenesis-related disease state? | A combination of biomarkers, imaging features, omics signatures, or multi-marker readouts is used to classify, predict, monitor, diagnose, or stratify thermogenic status. | A single marker is measured as part of a mechanism or modulation claim, with no panel/signature/clinical or translational assessment role. |
| 5 | `mechanism_pathway` | Through what molecular pathway is heat produced, regulated, transmitted, or linked to downstream signaling? | The claim describes signaling, transcriptional regulation, post-translational regulation, metabolic chemistry, ion/proton flow, oxygen consumption, UCP1-dependent or UCP1-independent heat generation, or a mechanistic chain tied to thermogenesis. | The main point is a broader cell function outcome, which should be `pathway_cellular_function_impact`, or an explicit organelle-organelle interaction, which should be `organelle_interaction_impact`. |
| 6 | `pathway_cellular_function_impact` | How does thermogenesis abnormality or a thermogenic pathway affect cellular pathways and cell functions? | A thermogenesis-related pathway changes cell differentiation, proliferation, apoptosis, autophagy, mitochondrial biogenesis, oxidative metabolism, inflammatory state, stress response, senescence, secretion, or other cell-level function. | The claim only says thermogenesis increased/decreased, without a broader cellular function consequence. |
| 7 | `organelle_interaction_impact` | Under mitochondrial thermogenesis abnormality or thermogenesis-related states, do interactions between organelles change, and how do they affect thermogenic state, metabolic state, or cellular function? | The claim explicitly involves organelle-organelle interactions, including mitochondria-other organelle interactions or interactions among non-mitochondrial organelles, and links them to thermogenesis, heat stress, metabolic rewiring, cellular function, calcium/lipid transfer, mitophagy, fission/fusion, autophagy, or stress signaling. | The text only describes general organelle biology without thermogenesis, heat stress, metabolic state, or cell-function relevance. |

## Overlap Rules

Use these rules when one sentence appears to fit more than one type.

1. If the main claim is about a measurement method, choose `detection_method`.
2. If the main claim is about an external or experimental intervention changing thermogenesis, choose `thermogenesis_modulation`.
3. If the main claim is about the internal molecular chain behind thermogenesis, choose `mechanism_pathway`.
4. If the main claim is about a downstream cellular function caused by a thermogenic pathway, choose `pathway_cellular_function_impact`.
5. If the main claim explicitly centers on organelle-organelle interaction under a thermogenesis, heat-stress, metabolic, or cell-function context, choose `organelle_interaction_impact`.
6. If the main claim links a disease/pathological state to thermogenic dysfunction, choose `disease_association`.
7. If the main claim uses multiple markers as an assessment signature, choose `biomarker_panel`.

## Practical Boundary Examples

### UCP1 mRNA increased

If the paper only reports UCP1 mRNA/protein change:

```text
mechanism_pathway
```

If UCP1 change is part of a measured thermogenic output after an intervention:

```text
thermogenesis_modulation
```

### Western blot / qPCR / immunofluorescence

If these are routine supporting methods:

```text
Do not create detection_method.
Attach the measurement details to the biological evidence unit.
```

If the paper introduces or validates the method itself as a thermogenesis measurement method:

```text
detection_method
```

### Mitochondrial biogenesis

If mitochondrial biogenesis is the downstream cell-function consequence of a thermogenic pathway:

```text
pathway_cellular_function_impact
```

If the paper explains the signaling route that causes thermogenesis:

```text
mechanism_pathway
```

### Organelle interaction under thermogenic or metabolic context

If the claim explicitly discusses mitochondria-ER contact, mitochondria-lipid droplet interaction, lysosome-lipid droplet interaction, ER-lipid droplet interaction, autophagosome-lysosome interaction, or other organelle-organelle interaction in a thermogenesis, heat-stress, metabolic, or cell-function context:

```text
organelle_interaction_impact
```

If it only says calcium/lipid/stress signaling regulates thermogenesis without organelle interaction:

```text
mechanism_pathway
```

## Stable Enum List

The current contract enum remains:

```text
disease_association
detection_method
thermogenesis_modulation
biomarker_panel
mechanism_pathway
pathway_cellular_function_impact
organelle_interaction_impact
```
