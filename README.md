# Champselect 2.0
This project aims to automate the process of queuing for a match of League of Legends. Here's a step-by-step rundown of how it works:

1. Prompt the user for what champion they'd like to play, which one they want to ban, and whether or not they  want the script to set their runes and summoner spells. 
2. Attempt to start queueing for a match _once_. If the user cancels the queue, it won't be started again. If the user is not the host of the lobby, this does nothing.
3. When the prompt appears, accept the match and check what role the user was queueing for
4. Once in champselect, hover the desired champion during the planning phase. If the user was autofilled (assigned a different role than the primary role they were queuing for), instead hover a champion from a config file with backup champions listed for each role.
5. During the ban phase, ban the champion the user specified. If the user was autofilled, or a teammate intends to play the specified champion, instead ban a champion from their config.
6. During the pick phase, attempt to lock in the champion currently being hovered. If it was banned, check config for a new one.
7. During the finalization phase, if the user said yes when prompted earlier, set their runes and summoner spells based on the champion they're playing and their assigned position.

The script is _intended_ to be used only normal draft and ranked. However, it can be used to automatically accept queues for other gamemodes as well, with some caveats listed below:

# Limitations
1. Breaks in tournament draft
2. Not guaranteed to work for non-draft modes or custom games (as of the time of writing, 5/27/25, it works for other gamemodes, but that could change)
3. No GUI
4. Runes are pulled directly from the client, so they're usually not very good

# Goals for the project
Because drafting in champselect is an important part of the game, I don't necessarily encourage the use of this project, especially for ranked. I mostly made it because I thought it would be fun, a good learning experience, and occasionally useful.
