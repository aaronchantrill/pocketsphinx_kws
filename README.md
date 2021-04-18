---
id: pocketsphinx_kws
label: Pocketsphinx_KWS
title: Pocketsphinx_KWS - Speech to Text
type: stts
description: "Allows Naomi to use pocketsphinx keyword spotting mode for passive listening"
logo: images/plugins/
source: https://github.com/aaronchantrill/pocketsphinx_kws.gitblob/master/readme.md
meta:
  - property: og:title
    content: "Pocketsphinx_KWS - Speech to Text"
  - property: og:description
    content: "Allows Naomi to use pocketsphinx keyword spotting mode for passive listening"
---

# Pocketsphinx_KWS - Speech to Text

<PluginLogo/>

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
        NAOMI: 25
        MAGICVOICE: 20
```

When you use this plugin, it will automatically create a vocabulary
including a thresholds file called kws.thresholds. The thresholds file has a
format like:

```
NAOMI   /1e+25/
MAGICVOICE  /1e+20/
```

If you have defined thresholds in your profile, they will be used when
creating the thresholds file.

<EditPageLink/>
