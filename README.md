# Discord Role Management Bot

This project is a Discord bot designed to manage user roles within a server. It provides functionality to add and remove roles while adhering to specific restrictions such as not allowing certain roles to be added or removed, and maintaining correct role hierarchy. Additionally, it allows for configurable restricted roles via environment variables.

## Features

- Add roles to users via commands.
- Enforce role restrictions (`@everyone` and configurable roles via an environment variable).
- Handle special cases, such as keeping the `RPC` role if it's already assigned.
- Check and manage role hierarchy, removing lower roles when a higher role is added.
- Supports dynamic management of restricted roles through environment variables.

    ### Planned Features

    - Aviation Weather retrieval
    - Australian ATIS retrieval
    - IFR route planning
    - VFR route planning

## Setup

### Prerequisites

- Discord bot token
- Docker

### Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/BenAChilds/pilot-bot.git
    cd discord-role-bot
    ```

2. **Create a Discord Developer bot**

    Navigate to Discord's developer portal and create your own application in order to obtain your token.
    The bot requires the following permissions;
    - **Manage Roles**: To assign and remove roles from users.
    - **View Channels**: To read messages in text channels.
    - **Send Messages**: To respond to commands and send feedback to users.
    - **Read Message History**: To interact with previous messages.
    - **Embed Links**: To display rich embeds when responding to commands.
    - **Ban Members**: If the bot will manage banning users.

    Copy your bot's token and use it in the next step.

2. **Set up environment variables:**

    Renamed `docker-compose.yml.new` to `docker-compose.yml` and update the environment variables with your values.

    The role `@everyone` is statically restricted, but any additional roles can be set via the `RESTRICTED_ROLES` environment variable.

3. **Create your welcome message**

    Rename `welcome_message.md.new` to `welcome_message.md` and update the file with the message you want to show your users when they join your server.

4. **Run the bot:**

    On Windows, open a terminal in the directory containing the code and run `.\rebuild.bat`.
    On Linux or Mac, open a terminal in the directory and run `./rebuild.sh`.

## Commands

### `!role add <role>`
- **Description**: Adds the specified role to the user.
- **Example**: `!role add CPL`

### `!role remove <role>`
- **Description**: Removes the specified role from the user.
- **Example**: `!role remove CPL`

### Role Restrictions
- The role `@everyone` is always restricted and cannot be added or removed.
- Additional restricted roles are defined via the `RESTRICTED_ROLES` environment variable.

## Contributing

Feel free to open issues or submit pull requests if you find bugs or have suggestions for improvements!

## License

This project is licensed under the GPL v3 License. See the [LICENSE](LICENSE) file for details.
