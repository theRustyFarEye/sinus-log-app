# Moonlit Sinus Log

Installable web app for logging daily sinus and hay fever symptoms against moon phase, local weather and pollen. By theRustyFarEye.

- **Use it:** https://therustyfareye.github.io/sinus-log-app/
- **Install:** Android Chrome → menu → *Install app*. iPhone Safari → Share → *Add to Home Screen*. Windows Edge/Chrome → install icon in the address bar.
- **Your data:** entries stay on your device (Settings → *Download backup* to keep a copy). Optionally, each device can sync to your own private GitHub repo with a fine-grained token stored only on that device. This repo holds no personal data.
- **Weather:** [Open-Meteo](https://open-meteo.com/), fetched by your device for your home town, or for where you are when the arrow button is on. Entries saved with location on store a rounded location (about 1 km) and that place's weather. Place names come from BigDataCloud; town search from Open-Meteo.
- **Pollen:** weekly counts from the [UCT Lung Institute](https://pollencount.co.za/report/) sampling site nearest to you (within 100 km). `data/pollen.json` publishes only the levels read from each report (low / moderate / high, dominant tree) with a link back to the full report. It's updated daily by the *Weekly pollen levels* Action.
- **Feedback:** Help & feedback in the app. Without a form key it opens the phone's share sheet so the message can go by WhatsApp or email.
