# The purpose of Lugha is to <b><u>evaluate language competence</u></b>

We believe that anybody can learn to speak
a language conversationally within 3 months.
This requires a high level of intensity & discipline.
By regularly evaluating your language competence,
you receive feedback quickly & speed up
your pace of learning. For additional accountability,
you can share access to your evaluations with others.

## Description

Lugha is a website where users can chat with an AI.
In a conversation format, a user sends written or
spoken text and receives a reply.
The chat interface is self-hosted
(and not e.g. served via Telegram or Facebook Messenger).
The UX is <b><u>optimised for a mobile experience</u></b>.
As AI, we currently use groq.com’s free LLM API.

Lugha has several frontend components:

- A welcome screen to set your language
  and conversation topic.
- A chat screen for chatting.
- An evaluation screen for reading
  the AI’s language competence evaluation.
- A log screen to see past conversations
  & evaluations as well as summary statistics.
- A coach screen where past conversations
  & evaluations as well as summary
  statistics of a user can be shown.

### Welcome

Very simple screen with few options.
Initially, set a name, a language and a theme.
Start the conversation.

<img src="./files/lugha-sketch-initial.png" alt="lugha-sketch-initial.png" width="25%" />

### Chat

Total focus on the conversation itself.
There are only 2 options: 1) Send a message (send icon)
or 2) finish your conversation
& get an evaluation (top bar in red).

<img src="./files/lugha-sketch-chat.png" alt="lugha-sketch-chat.png" width="25%" />

### Evaluation

After finishing a conversation,
see your evaluation and the now locked conversation.

A user can receive an evaluation only if the total number
of words sent by the user exceeds 10 words.
If this criterion isn't met, the user sees this friendly message:
*"Your conversation didn’t meet the criteria for evaluation.
Please send at least 10 words to receive a meaningful feedback."*

<img src="./files/lugha-sketch-evaluation.png" alt="lugha-sketch-evaluation.png" width="25%" />

### Log

The log screen shows a full list of all
past (now locked) conversations and their evaluations
(see evaluation screen). A user can initiate
a new conversation here. When he clicks “NEW”,
the user sees the same options as on the Welcome screen.
Also, a user can see a graph that depicts his
progress.

#### Progress graph

A **bar chart** presents a multivariable analysis:

- **X-axis**: Dates (day/month).
- **Y-axis**: Overall scores (0%–100%) for each day
(calculated as the average rating of all conversations for that day).

Additional details:

- Bars display total conversation duration (in minutes) at the top.
- Scores and durations are stored in a database.
- A **horizontal scrollbar** allows exploration of historical data.

**Note:** The dashboard appears after **7 days** of usage.
Before then, users see:
*"You’ll receive visualizations of your progress after completing 7 days of conversations."*

**Optimization:**
To enhance dashboard performance, we created a dedicated table with these columns:

- **Date**: Stores the day (date only, no time).
- **Overall Score**: Aggregated from the evaluation field for all conversations on that day.
- **Total Duration**: Sum of all conversation durations for that day in minutes.

This table auto-updates after each completed conversation, ensuring real-time data without repeated fetching or calculations.

#### Dashboard Features

A **bar chart** presents a multivariable analysis:

- **X-axis**: Dates (day/month).
- **Y-axis**: Overall scores (0%–100%) for each day
(calculated as the average rating of all conversations for that day).

Additional details:

- Bars display total conversation duration (in minutes) at the top.
- Scores and durations are stored in a database.
- A **horizontal scrollbar** allows exploration of historical data.

**Note:** The dashboard appears after **7 days** of usage.
Before then, users see:
*"You’ll receive visualizations of your progress after completing 7 days of conversations."*

**Optimization:**
To enhance dashboard performance, we created a dedicated table with these columns:
- **Date**: Stores the day (date only, no time).
- **Overall Score**: Aggregated from the evaluation field for all conversations on that day.
- **Total Duration**: Sum of all conversation durations for that day in minutes.

This table auto-updates after each completed conversation, ensuring real-time data without repeated fetching or calculations.

<img src="./files/lugha-sketch-log.png" alt="lugha-sketch-log.png" width="25%" />

### Coach

The coach screen shows a dropdown where a coach
can select a user name, whose log is then shown.

<img src="./files/lugha-sketch-coach.png" alt="lugha-sketch-coach.png" width="25%" />

## Monitoring: Uptime & usage KPIs

We need an easy-to-maintain and flexible set-up
to monitor uptime & usage. Initially (and maybe forever)
we’ll set up a Telegram webhook to periodically check
if the app is available. If it is unavailable,
it sends a Telegram message to the admins.
It also checks usage statistics. Once a week, it sends an
"I'm alive message" and provides summary statistics.

## Database design

To improve data organization and query efficiency, we are transforming the database into a **star schema model**.

#### Conversations_parameters
- **conversation_id** (Primary Key)
- **user_name**
- **created_at**
- **language**
- **theme**
- **start_time**
- **user_prompt**
- **bot_messages**



#### Conversations_evaluations
- **conversation_id**
- **evaluation**
- **end_time**
- **duration**
- **interaction_count**
