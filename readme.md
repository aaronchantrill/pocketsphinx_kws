---
id: pocketsphinx_kws
label: Pocketsphinx_KWS
title: Pocketsphinx_KWS - Speech to Text
type: stts
description: "Allows Naomi to use pocketsphinx keyword spotting mode for passive listening"
source: https://github.com/aaronchantrill/pocketsphinx_kws.gitblob/master/readme.md
meta:
  - property: og:title
    content: "Pocketsphinx_KWS - Speech to Text"
  - property: og:description
    content: "Allows Naomi to use pocketsphinx keyword spotting mode for passive listening"
---

# Pocketsphinx_KWS - Speech to Text

This plugin uses thresholds to listen for specific words. It is primarily meant
to be used to listen for keywords or wakewords, although if you have an
application with a very limited vocabulary (such as a robot that responds to
"left", "right", "forward", and "stop") you can use it for the full vocabulary.

In Naomi, we will use it to listen for the wake word(s).

To activate this plugin, change your profile.yml file to set the passive
listener engine like this:

```
keyword:
- NAOMI
- MAGICVOICE
passive_stt:
  engine: Pocketsphinx_KWS
Pocketsphinx_KWS:
    thresholds:
        naomi: -10
        magicvoice: -50
```
(notice that under the thresholds section, the keywords should be all lower
case).

When you use this plugin, it will automatically create a vocabulary
including a thresholds file called kws.thresholds. The thresholds file has a
format like:

```
naomi   /1e-10/
magicvoice  /1e-50/
```

If you have defined thresholds in your profile, they will be used when
creating the thresholds file. If any of your wake words are being activated
accidentally too often, try increasing the threshold. If Naomi becomes too
difficult to activate, try decreasing the threshold. The range of valid
threshold levels is from negative eighty to eighty. I am working on a
trainer called Pocketsphinx_KWS_Trainer. When it is available, you can use
the recordings and verified transcripts to help select the best thresholds.

This also shares the "sphinx" acoustic model, so using the "Adapt Pocketsphinx"
STT Trainer plugin is highly recommended for training Naomi to your voice.

<EditPageLink/>
