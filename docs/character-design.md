# BrainBob character design

Research and design direction, October 17, 2026. Use a bright yellow rounded rectangle, a readable graphic face, and wide violet pants. Keep a circular body and a gentle parallelogram available in the character study for comparison. Cuteness depends on the relationship between features; adding more blush, shine, or larger eyes is not a reliable formula.

## What the evidence supports

| Finding | Evidence and limits | Design inference for BrainBob |
| --- | --- | --- |
| Infant-like facial proportions can increase perceived cuteness. | Glocker et al. manipulated infant photographs with a combination of rounder faces, higher foreheads, larger eyes, and smaller noses and mouths. Higher baby-schema versions received higher cuteness ratings. The analyzed samples were 62 participants for cuteness and 44 for caretaking motivation. This does not isolate a single feature or establish optimal mascot proportions. [Glocker et al., 2009](https://www.med.upenn.edu/csa/assets/user-content/documents/BabySchemainInfantFacesInducesCutenessPerceptionandMotivationforCaretakinginAdults.pdf) | Leave generous forehead space, keep the face compact, and give the eyes room. Avoid enlarging every feature together. |
| Curved contours can be more appealing than sharp contours. | Bar and Neta found a preference for curved over sharp-angled visual objects. This is evidence about object preference, not a direct test of mascot cuteness or a guarantee that every round character works. [Bar & Neta, 2006](https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.2006.01759.x/) | Use one soft silhouette, rounded hands, and short boots. Keep small decorative geometry from breaking that silhouette. |
| Inconsistent realism can make a face unsettling. | Across experiments with computer-generated human faces, MacDorman et al. found atypical proportions more disturbing with photorealistic textures; mismatches involving eye and face size or texture were especially prone to eeriness. Their human-face results do not diagnose a yellow cartoon character. [MacDorman et al., 2009](https://doi.org/10.1016/j.chb.2008.12.026) | Give the eyes, mouth, body, and clothing the same toy-like visual language. Favor shallow graphic features over layered eyeball-like forms. |

These are useful starting hypotheses, not universal laws. The studies involve particular participants and stimuli; they do not establish that one design appeals to every culture, age, or person. Bright yellow is the requested identity choice, not an experimentally proven cuteness treatment.

## Diagnosis of the previous plush iteration

This is a design assessment of the existing mesh and room screenshot, not a measured psychological diagnosis:

- Cream eye rims, dark eye volumes, and two highlights per eye concentrate detail around the stare while the body remains very simple. This can suggest a doll face rather than a cheerful graphic mascot.
- The smile becomes hard to see at the room's normal camera distance. The eyes dominate when the expression disappears.
- Pale yellow blends into the cream floor and lighting. Restoring saturated yellow improves identity and separation without adding detail.
- A nearly spherical body needs confident proportions and restrained motion. Extra wobble or swelling would reinforce the user's impression of an inflated character.

## Practical design checklist

The following are proposed art-direction and animation choices, informed by the evidence above but not directly tested by those studies:

- Use the restored vivid yellow body (`#FFD21F`), matte shading, and violet workwear.
- Place two dark, shallow eyes slightly lower on the face, leaving more forehead. Remove cream rims and multiple sparkles; one small highlight is enough.
- Keep a small, clear smile with sufficient contrast to survive the default camera distance. Avoid realistic teeth, lips, skin texture, or a protruding human nose.
- Keep rounded corners, short limbs, rounded hands, and stable feet. Curved contours do not require a spherical body. A rounded rectangle leaves a broad face and stable arm attachment points; a gentle parallelogram adds a lean. Wide, shallow rectangular pants keep the lower silhouette distinct.
- Match steps to travel speed, ease turns, and use brief pauses and occasional blinks. Limit body bounce; avoid rhythmic inflation or constant jitter.
- Reserve role differences for one accessory or a carried document. Keep the base face consistent.

## How to judge the revision

Review a still image and a short motion sample at both close-up and normal room scale. Compare against the previous version under the same camera and lighting. Ask viewers separately whether it feels **friendly**, **clear**, and **unsettling**, and what feature caused that impression. Check that the smile remains visible, the yellow stays distinct from the room, and the feet appear grounded. These checks are an evaluation plan; no user-study results are claimed.

## Current implementation

The [character study](http://127.0.0.1:3000/character-study) uses the same face, color, pants, and lighting for all three silhouettes. The user selected the rounded rectangle, now the room's default. Its graphic face removes the previous layered eyeballs, keeps one highlight per eye, and makes the smile visible. The body does not inflate during movement. Feet take small distance-driven steps, turns follow the shortest angle, and the face blinks briefly. The movement toggle and system reduced-motion preference stop ambient animation.

## Design for emotions and actions

Keep four concerns separate: **locomotion**, **task pose**, **expression**, and **props**. The current procedural model already separates the body, face material, arm pivots, and feet. Named `left-hand-socket` and `right-hand-socket` groups provide stable prop attachment points; carried paper follows the right arm. This is a small procedural rig, not a finished skeletal animation system.

For the next animation layer, give each action an event ID, actor ID, target, progress, and optional partner. An action controls the relevant arm instead of competing with the walking swing. Add wrist/elbow reach where interaction demands it, keeping the resting silhouette compact. Swap facial drawings on the same surface for focused, curious, puzzled, pleased, and attentive expressions. Keep expressions readable at room scale and use exaggerated poses sparingly.

| Action | Pose and props | Expression and event relationship |
| --- | --- | --- |
| Store a new memory | Carry paper, open the target drawer, slide it into a cabinet slot, close the drawer. | Focused during filing; pleased after the recorded create succeeds. |
| Write or revise | Stand at a desk, hold paper with one hand, move a pen with the other. | Concentrated eyes and a small calm mouth; corrected record is filed after update commits. |
| Forget | Carry the retired paper to a disposal tray; let its visual copy curl and burn away. | Calm release rather than panic. Play only after archival succeeds; history remains available. Fire belongs to the paper, not the character or room. |
| Teach | Face another worker, point at a shared document or small board, pause for a response. | Engaged and encouraging. Depicts a recorded explanation or handoff, not proof of learning. |
| Learn | Look toward the teacher, take notes, then acknowledge. | Attentive, then pleased. Show a learned result only when the corresponding check is recorded. |
| Resolve a conflict | Compare two papers, tilt the body slightly, present the discrepancy. | Puzzled until evidence resolves it; no permanent alarm state. |

These actions and additional expressions are **planned**. Walking, blinking, arm motion, and carried paper are implemented. Keep task animations tied to recorded results, with deterministic playback for retracing; animation completion must never create or delete a memory. Reduced motion should show the final pose and a readable event description, without flame particles or repeated gestures.
