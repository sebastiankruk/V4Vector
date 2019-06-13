# V4Vector



## Installing V for Vector

1. You will need Python 3.7+.
1. Checkout out source code from [github](https://github.com/sebastiankruk/V4Vector):

    ```bash
    git clone https://github.com/sebastiankruk/V4Vector.git
    ```

1. Prepare virtual environment:

    ```bash
    virtualenv -p /usr/local/bin/python3 --no-site-packages .env
    ```



1. Setup your environment:

    * Copy `jira-connection-template.json` to `jira-connection.json` and specify JIRA url and your credentials as basic token
    * Copy `jira-users-template.json` to `jira-users.json` and specify mappings between Vector users and Jira users
    