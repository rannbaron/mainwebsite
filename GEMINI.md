# Main Website & Early Voting Swing Map Repository Rules

- **Workspace Scope**: This repository (`~/src/website/mainwebsite/`) is reserved for the primary `rannbar-on.com` website source, including the early voting swing explorer, data ingestion pipelines, GIS files, and GitHub Pages deployment workflows.
- **Strict Project Isolation**: Never generate or edit files belonging to other projects in this directory.
- **Related Project Paths**:
  - NC Student Voting Info Platform: `~/src/website/voting-info/`
  - NC Trivia Flashcards: `~/src/website/nctrivialflash/`
  - Math 105L Teaching: `~/Documents/math/teaching/105L/Fall26/`
- **Output Protocol**: All scripts and generators must output exclusively within their designated project target directories.

## Task Priority Dashboard Notification Protocol
- **Strict Email Destination**: ALL task dashboard notifications, registration alerts, admin approval requests, task queues, and 2FA dispatches MUST go exclusively to `rann@rannbar-on.com`.
- **No rb6 Destination**: Never send, CC, or dispatch any dashboard notifications or alerts to `rb6` or `rb6@duke.edu`.
