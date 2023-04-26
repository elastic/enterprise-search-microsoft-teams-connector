![](logo-enterprise-search.png)

[Elastic Enterprise Search](https://www.elastic.co/guide/en/enterprise-search/current/index.html) | [Elastic Workplace Search](https://www.elastic.co/guide/en/workplace-search/current/index.html)

# Microsoft Teams connector package

Use this _Elastic Enterprise Search Microsoft Teams connector package_ to deploy deploy and run a Microsoft Teams connector on your own infrastructure. The connector extracts and syncs data from your [Microsoft Teams](https://www.microsoft.com/en/microsoft-teams/group-chat-software) application. The data is indexed into a Workplace Search content source within an Elastic deployment.

⚠️ _This connector package is a **beta** feature._
Beta features are subject to change and are not covered by the support SLA of generally available (GA) features. Elastic plans to promote this feature to GA in a future release.

ℹ️ _This connector package requires a compatible Elastic subscription level._
Refer to the Elastic subscriptions pages for [Elastic Cloud](https://www.elastic.co/subscriptions/cloud) and [self-managed](https://www.elastic.co/subscriptions) deployments.

**Table of contents:**

- [Setup and basic usage](#setup-and-basic-usage)
  - [Gather Microsoft Teams details](#gather-microsoft-teams-details)
  - [Gather Elastic details](#gather-elastic-details)
  - [Create a Workplace Search API key](#create-a-workplace-search-api-key)
  - [Create a Workplace Search content source](#create-a-workplace-search-content-source)
  - [Choose connector infrastructure and satisfy dependencies](#choose-connector-infrastructure-and-satisfy-dependencies)
  - [Install the connector](#install-the-connector)
  - [Configure the connector](#configure-the-connector)
  - [Test the connection](#test-the-connection)
  - [Sync data](#sync-data)
  - [Log errors and exceptions](#log-errors-and-exceptions)
  - [Schedule recurring syncs](#schedule-recurring-syncs)
- [Troubleshooting](#troubleshooting)
  - [Troubleshoot extraction](#troubleshoot-extraction)
  - [Troubleshoot syncing](#troubleshoot-syncing)
  - [Troubleshoot Access Token Generation](#troubleshoot-access-token-generation)
- [Advanced usage](#advanced-usage)
  - [Customize extraction and syncing](#customize-extraction-and-syncing)
  - [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)
- [Connector reference](#connector-reference)
  - [Data extraction and syncing](#data-extraction-and-syncing)
  - [Sync operations](#sync-operations)
  - [Command line interface (CLI)](#command-line-interface-cli)
  - [Configuration settings](#configuration-settings)
  - [Enterprise Search compatibility](#enterprise-search-compatibility)
  - [Runtime dependencies](#runtime-dependencies)
- [Connector Limitations](#connector-limitations)

## Setup and basic usage

Complete the following steps to deploy and run the connector:

1. [Gather Microsoft Teams details](#gather-microsoft-teams-details)
1. [Gather Elastic details](#gather-elastic-details)
1. [Create a Workplace Search API key](#create-a-workplace-search-api-key)
1. [Create a Workplace Search content source](#create-a-workplace-search-content-source)
1. [Choose connector infrastructure and satisfy dependencies](#choose-connector-infrastructure-and-satisfy-dependencies)
1. [Install the connector](#install-the-connector)
1. [Configure the connector](#configure-the-connector)
1. [Test the connection](#test-the-connection)
1. [Sync data](#sync-data)
1. [Log errors and exceptions](#log-errors-and-exceptions)
1. [Schedule recurring syncs](#schedule-recurring-syncs)

The steps above are relevant to all users. Some users may require additional features. These are covered in the following sections:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Gather Microsoft Teams details

Collect the information that is required to connect to Microsoft Teams:

- The username the connector will use to log in to Microsoft Teams.
- The password the connector will use to log in to Microsoft Teams.
- The `client id` or `application id` from Microsoft Azure.
- The application's `client secret` from Microsoft Azure.
- The application's `tenant id` from Microsoft Azure.

ℹ️ You must use the `username` and `password` for the Microsoft Teams admin account.

Later, you will [configure the connector](#configure-the-connector) with these values.

ℹ️ The connector uses the [MSAL](https://msal-python.readthedocs.io/en/latest/) module to generate access tokens, used for fetching documents from Microsoft Teams.

Some connector features require additional details. Review the following documentation if you plan to use these features:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Gather Elastic details

First, ensure your Elastic deployment is [compatible](#enterprise-search-compatibility) with the Microsoft Teams connector package.

Next, determine the [Enterprise Search base URL](https://www.elastic.co/guide/en/enterprise-search/current/endpoints-ref.html#enterprise-search-base-url) for your Elastic deployment.

Later, you will [configure the connector](#configure-the-connector) with this value.

You also need a Workplace Search API key and a Workplace Search content source ID. You will create those in the following sections.

If you plan to use document-level permissions, you will also need user identity information. See [Use document-level permissions (DLP)](#use-document-level-permissions-dlp) for details.

### Create a Workplace Search API key

Each Microsoft Teams connector authorizes its connection to Elastic using a Workplace Search API key.

Create an API key within Kibana. See [Workplace Search API keys](https://www.elastic.co/guide/en/workplace-search/current/workplace-search-api-authentication.html#auth-token).

### Create a Workplace Search content source

Each Microsoft Teams connector syncs data from Microsoft Teams into a Workplace Search content source.

Create a content source within Kibana:

1. Navigate to **Enterprise Search** → **Workplace Search** → **Sources** → **Add Source** → **Microsoft Teams**.
2. Choose **Configure Microsoft Teams**.

For more details please refer [Elastic Documentation for creating a custom content source](https://www.elastic.co/guide/en/workplace-search/current/workplace-search-custom-api-sources.html#create-custom-source).

Record the ID of the new content source. This value is labeled *Source Identifier* within Kibana. Later, you will [configure the connector](#configure-the-connector) with this value.

**Alternatively**, you can use the connector's `bootstrap` command to create the content source. See [`bootstrap` command](#bootstrap-command).

### Choose connector infrastructure and satisfy dependencies

After you’ve prepared the two services, you are ready to connect them.

Provision a Windows, MacOS, or Linux server for your Microsoft Teams connectors.

The infrastructure must provide the necessary runtime dependencies. See [Runtime dependencies](#runtime-dependencies).

Clone or copy the contents of this repository to your infrastructure.

### Install the connector

After you’ve provisioned infrastructure and copied the package, use the provided `make` target to install the connector:

```shell
make install_package
```

This command runs as the current user and installs the connector and its dependencies.
Note: By Default, the package installed supports Enterprise Search version 8.0 or above. In order to use the connector for older versions of Enterprise Search(less than version 8.0) use the ES_VERSION_V8 argument while running make install_package or make install_locally command:

```shell
make install_package ES_VERSION_V8=no
```

ℹ️ Within a Windows environment, first install `make`:

```
winget install make
```

Next, ensure the `ees_microsoft_teams` executable is on your `PATH`. For example, on macOS:

```shell
export PATH=/Users/shaybanon/Library/Python/3.8/bin:$PATH
```

The following table provides the installation location for each operating system (note Python version 3.8):

| Operating system | Installation location                                        |
| ---------------- | ------------------------------------------------------------ |
| Linux            | `./local/bin`                                                |
| macOS            | `/Users/<user_name>/Library/Python/3.8/bin`                  |
| Windows          | `\Users\<user_name>\AppData\Roaming\Python\Python38\Scripts` |

### Configure the connector

You must configure the connector to provide the information necessary to communicate with each service. You can provide additional configuration to customize the connector for your needs.

Create a [YAML](https://yaml.org/) configuration file at any pathname. Later, you will include the [`-c` option](#-c-option) when running [commands](#command-line-interface-cli) to specify the pathname to this configuration file.

_Alternatively, in Linux environments only_, locate the default configuration file created during installation. The file is named `microsoft_teams_connector.yml` and is located within the `config` subdirectory where the package files were installed. See [Install the connector](#install-the-connector) for a listing of installation locations by operating system. When you use the default configuration file, you do not need to include the `-c` option when running commands.

After you’ve located or created the configuration file, populate each of the configuration settings. Refer to the [settings reference](#configuration-settings). You must provide a value for all required settings.

Use the additional settings to customize the connection and manage features such as document-level permissions. See:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Test the connection

After you’ve configured the connector, you can test the connection between Elastic and Microsoft Teams. Use the following `make` target to test the connection:

```shell
make test_connectivity
```

### Sync data

After you’ve confirmed the connection between the two services, you are ready to sync data from Microsoft Teams to Elastic.

The following table lists the available [sync operations](#sync-operations), as well as the [commands](#command-line-interface-cli) to perform the operations.

| Operation                             | Command                                         |
| ------------------------------------- | ----------------------------------------------- |
| [Incremental sync](#incremental-sync) | [`incremental-sync`](#incremental-sync-command) |
| [Full sync](#full-sync)               | [`full-sync`](#full-sync-command)               |
| [Deletion sync](#deletion-sync)       | [`deletion-sync`](#deletion-sync-command)       |

Begin syncing with an *incremental sync*. This operation begins [extracting and syncing content](#data-extraction-and-syncing) from Microsoft Teams to Elastic. If desired, [customize extraction and syncing](#customize-extraction-and-syncing) for your use case.

Review the additional sync operations to learn about the different types of syncs. Additional configuration is required to use [document-level permissions](#use-document-level-permissions-dlp).

You can use the command line interface to run sync operations on demand, but you will likely want to [schedule recurring syncs](#schedule-recurring-syncs).

### Log errors and exceptions

The various [sync commands](#command-line-interface-cli) write logs to standard output and standard error.

To persist logs, redirect standard output and standard error to a file. For example:

```shell
ees_microsoft_teams -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
```

You can use these log files to implement your own monitoring and alerting solution.

Configure the log level using the [`log_level` setting](#log_level).

### Schedule recurring syncs

Use a job scheduler, such as `cron`, to run the various [sync commands](#command-line-interface-cli) as recurring syncs.

The following is an example crontab file in linux:	

```crontab	
PATH=/home/<user_name>/.local/bin

0 */2 * * * ees_microsoft_teams -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
0 0 */2 * * ees_microsoft_teams -c ~/config.yml full-sync >>~/full-sync.log 2>&1
0 * * * * ees_microsoft_teams -c ~/config.yml deletion-sync >>~/deletion-sync.log 2>&1
```

This example redirects standard output and standard error to files, as explained here: [Log errors and exceptions](#log-errors-and-exceptions).

Use this example to create your own crontab file. Manually add the file to your crontab using `crontab -e`. Or, if your system supports cron.d, copy or symlink the file into `/etc/cron.d/`.

⚠️ **Note**: It's possible that scheduled jobs may overlap.
To avoid multiple crons running concurrently, you can use [flock](https://manpages.debian.org/testing/util-linux/flock.1.en.html) with cron to manage locks. The `flock` command is part of the `util-linux` package. You can install it with `yum install util-linux`
or `sudo apt-get install -y util-linux`.
Using flock ensures the next scheduled cron runs only after the current one has completed execution. 

Let's consider an example of running incremental-sync as a cron job with flock:

```crontab
0 */2 * * * /usr/bin/flock -w 0 /var/cron_indexing.lock ees_microsoft_teams -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
```

Note: If the flock is added for multiple commands in crontab, make sure you mention different lock names(eg: /var/cron_indexing.lock in the above example) for each job else the execution of one command will prevent other command to execute.

## Troubleshooting

To troubleshoot an issue, first view your [logged errors and exceptions](#log-errors-and-exceptions).

Use the following sections to help troubleshoot further:

- [Troubleshoot extraction](#troubleshoot-extraction)
- [Troubleshoot syncing](#troubleshoot-syncing)
- [Troubleshoot Access Token Generation](#troubleshoot-access-token-generation)

If you need assistance, use the Elastic community forums or Elastic support:

- [Enterprise Search community forums](https://discuss.elastic.co/c/enterprise-search/84)
- [Elastic Support](https://support.elastic.co)

### Troubleshoot extraction

The following sections provide solutions for content extraction issues.

#### Issues extracting content from attachments

The connector uses the [Tika module](https://pypi.org/project/tika/) for parsing file contents from attachments. [Tika-python](https://github.com/chrismattmann/tika-python) uses Apache Tika REST server. To use this library, you need to have Java 7+ installed on your system as tika-python starts up the Tika REST server in the background.

At times, the TIKA server fails to start hence content extraction from attachments may fail. To avoid this, make sure Tika is running in the background.

#### Issues extracting content from images

Tika Server also detects contents from images by automatically calling Tesseract OCR. To allow Tika to also extract content from images, you need to make sure tesseract is on your path and then restart tika-server in the background (if it is already running). For example, on a Unix-like system, try:

```shell
ps aux | grep tika | grep server # find PID
kill -9 <PID>
```

To allow Tika to extract content from images, you need to manually install Tesseract OCR.

### Troubleshoot syncing

The following sections provide solutions for issues related to syncing.

## Advanced usage

The following sections cover additional features that are not covered by the basic usage described above.

After you’ve set up your first connection, you may want to further customize that connection or scale to multiple connections.

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

## Customize extraction and syncing

By default, each connection syncs all [supported Microsoft Teams data](#data-extraction-and-syncing) across all Microsoft Teams applications.

You can also customize which objects are synced, and which fields are included and excluded for each object. [Configure](#configure-the-connector) the setting [`object_type_to_index`](#object_type_to_index).

Finally, you can set custom timestamps to control which objects are synced, based on their created or modified timestamps. [Configure](#configure-the-connector) the following settings:

- [`start_time`](#start_time)
- [`end_time`](#end_time)

### Troubleshoot Access Token Generation

The following section provide the solution for issue related to access token generation.

## Disable Multi-factor Authentication
1. Go to **Microsoft Azure AD > Properties**.
2. Go to **Manage Security defaults**, disable security and save the changes.
3. Go to **Users** and create a new user with global permissions from assignees roles.
4. Go to **Microsoft Teams Azure AD Conditional access** and create a new policy:
- **Name:** Name of the policy
- **Users or workload identities:** include "allusers" and exclude the newly created users (this step will disable MFA for all excluded users).
- **Cloud apps or actions:** include "All cloud apps"
- **Grant:** select "grant access" with Require "multi-factor authentication" enabled and from multiple controls select "Require all the selected controls"
5. Enable the policy with "Yes" and save.

## Add permissions to Microsoft Azure Platform
1. Check the configuration file and verify all Microsoft Teams settings configuration values are set correctly.
2. If configuration values are set correctly, go to your application on Microsoft Azure Platform and verify all permissions are added as per the permission listed below and have the admin consent to each permission.
- `User.Read.All` (Delegated and Application)
- `TeamMember.Read.All` (Delegated)
- `Team.ReadBasic.All` (Delegated)
- `TeamsTab.Read.All` (Delegated)
- `Group.Read.All` (Delegated)
- `ChannelMessage.Read.All` (Delegated)
- `Chat.Read` (Delegated) & `Chat.Read.All` (Application)
- `Chat.ReadBasic` (Delegated) & `Chat.ReadBasic.All` (Application)
- `Files.Read.All` (Delegated and Application)
- `Calendars.Read` (Delegated and Application)

### Use document-level permissions (DLP)

Complete the following steps to use document-level permissions:

1. Enable document-level permissions
1. Map user identities
1. Sync document-level permissions data

#### Enable document-level permissions

Within your configuration, enable document-level permissions using the following setting: [`enable_document_permission`](#enable_document_permission).

#### Map user identities

Copy to your server a CSV file that provides the mapping of user identities. The file must follow this format:

- First column: Microsoft Teams username
- Second column: Elastic username

Then, configure the location of the CSV file using the following setting: [`microsoft_teams.user_mapping`](#microsoft_teams.user_mapping).

#### Sync document-level permissions data

Sync document-level permissions data from Microsoft Teams to Elastic.

The following sync operations include permissions data:

- [Incremental sync](#incremental-sync)
- [Full sync](#full-sync)

Sync this information continually to ensure correct permissions. See [Schedule recurring syncs](#schedule-recurring-syncs).

## Connector reference

The following reference sections provide technical details:

- [Data extraction and syncing](#data-extraction-and-syncing)
- [Sync operations](#sync-operations)
- [Command line interface (CLI)](#command-line-interface-cli)
- [Configuration settings](#configuration-settings)
- [Enterprise Search compatibility](#enterprise-search-compatibility)
- [Runtime dependencies](#runtime-dependencies)

### Data extraction and syncing

Each Microsoft Teams connector extracts and syncs the following data from Microsoft Teams:

- Teams
- Channels
- Channel Messages
- Channel Meetings
- Channel Tabs
- Channel Documents (Files/Folders)
- User Chat Messages
- User Chat Tabs
- User Chat Attachments
- Calendar Meetings (Meeting transcript won't get indexed)

The connector handles Microsoft Teams pages comprised of various web parts, it extracts content from various document formats, and it performs optical character recognition (OCR) to extract content from images.

You can customize extraction and syncing per connector. See [Customize extraction and syncing](#customize-extraction-and-syncing).

### Sync operations

The following sections describe the various operations to [sync data](#sync-data) from Microsoft Teams to Elastic.

#### Incremental sync

Syncs to Enterprise Search all [supported Microsoft Teams data](#data-extraction-and-syncing) *created or modified* since the previous incremental sync.

When [using document-level permissions (DLP)](#use-document-level-permissions-dlp), each incremental sync will also perform a [permission sync](#permission-sync).

Perform this operation with the [`incremental-sync` command](#incremental-sync-command).

#### Full sync

Syncs to Enterprise Search all [supported Microsoft Teams data](#data-extraction-and-syncing) *created or modified* since the configured [`start_time`](#start_time). Continues until the current time or the configured [`end_time`](#end_time).

Perform this operation with the [`full-sync` command](#full-sync-command).

#### Deletion sync

Deletes from Enterprise Search all [supported Microsoft Teams data](#data-extraction-and-syncing) *deleted* since the previous deletion sync.

Perform this operation with the [`deletion-sync` command](#deletion-sync-command).

#### Permission sync

Syncs to Enterprise Search all Microsoft Teams document permissions since the previous permission sync.

When [using document-level permissions (DLP)](#use-document-level-permissions-dlp), use this operation to sync all updates to users and groups within Microsoft Teams.

Perform this operation with the [`permission-sync` command](#permission-sync-command).

### Command line interface (CLI)

Each Microsoft Teams connector has the following command line interface (CLI):

```shell
ees_microsoft_teams [-c <pathname>] <command>
```

#### `-c` option

The pathname of the [configuration file](#configure-the-connector) to use for the given command.

```shell
ees_microsoft_teams -c ~/config.yml full-sync
```

#### `bootstrap` command

Creates a Workplace Search content source with the given name. Outputs its ID.

```shell
ees_microsoft_teams bootstrap --name 'Accounting documents' --user 'shay.banon'
```

See also [Create a Workplace Search content source](#create-a-workplace-search-content-source).

To use this command, you must [configure](#configure-the-connector) the following settings:

- [`enterprise_search.host_url`](#enterprise_searchhost_url-required)
- [`workplace_search.api_key`](#workplace_searchapi_key-required)

And you must provide on the command line any of the following arguments that are required:

- `--name` (required): The name of the Workplace Search content source to create.
- `--user` (optional): The username of the Elastic user who will own the content source. If provided, the connector will prompt for a password. If omitted, the connector will use the configured API key to create the content source.

#### `incremental-sync` command

Performs a [incremental sync](#incremental-sync) operation.

#### `full-sync` command

Performs a [full sync](#full-sync) operation.

#### `deletion-sync` command

Performs a [deletion sync](#deletion-sync) operation.

### Configuration settings

[Configure](#configure-the-connector) any of the following settings for a connector:

#### `username` (required)

The username of the admin account for the Microsoft Teams.

```yaml
username: username@t8zsn.onmicrosoft.com
```

#### `password` (required)

The password of the admin account for the Microsoft Teams. See [Gather Microsoft Teams details](#gather-microsoft-teams-details).

```yaml
password: 'L,Ct%ddUvNTE5zk;GsDk^2w)(;,!aJ|Ip!?Oi'
```

#### `application_id` (required)

The application id or client id of the newly created application from the Microsoft Azure Portal. See [Gather Microsoft Teams details](#gather-microsoft-teams-details).

```yaml
application_id: '1234a329-b7e5-4fb4-1234-123a095abc48'
```

#### `client_secret` (required)

The client secret of the newly created application from the Microsoft Azure Portal. See [Gather Microsoft Teams details](#gather-microsoft-teams-details).

```yaml
client_secret: <SECRET>
```

#### `tenant_id` (required)

The tenant id of the Microsoft Azure Portal. See [Gather Microsoft Teams details](#gather-microsoft-teams-details).

```yaml
tenant_id: '4321a329-b7e5-4fb4-1234-327a095olp48'
```

#### `workplace_search.api_key` (required)

The Workplace Search API key. See [Create a Workplace Search API key](#create-a-workplace-search-api-key).

```yaml
workplace_search.api_key: 'zvksftxrudcitxa7ris4328b'
```

#### `workplace_search.source_id` (required)

The ID of the Workplace Search content source. See [Create a Workplace Search content source](#create-a-workplace-search-content-source).

```yaml
workplace_search.source_id: '62461219647336183fc7652d'
```

#### `enterprise_search.host_url` (required)

The [Enterprise Search base URL](https://www.elastic.co/guide/en/enterprise-search/current/endpoints-ref.html#enterprise-search-base-url) for your Elastic deployment.

```yaml
enterprise_search.host_url: https://my-deployment.ent.europe-west1.gcp.cloud.es.io:9243
```

Note: While using Elastic Enterprise Search version 8.0.0 and above, port must be specified in [`enterprise_search.host_url`](#enterprise_searchhost_url-required)

#### `enable_document_permission`

Whether the connector should sync [document-level permissions (DLP)](#use-document-level-permissions-dlp) from Microsoft Teams.

```yaml
enable_document_permission: Yes
```

#### `object_type_to_index`

Specifies which Microsoft Teams objects to sync to Enterprise Search, and for each object, which fields to include and exclude. When the include/exclude fields are empty, all fields are synced.

```yaml
object_type_to_index:
  teams:
    include_fields:
    exclude_fields:
  channels:
    include_fields:
    exclude_fields:
  channel_messages:
    include_fields:
    exclude_fields:
  channel_documents:
    include_fields:
    exclude_fields:
  channel_tabs:
    include_fields:
    exclude_fields:
  user_chats:
    include_fields:
    exclude_fields:
  calendar:
    include_fields:
    exclude_fields:
```

#### `start_time`

A UTC timestamp the connector uses to determine which objects to extract and sync from Microsoft Teams. Determines the *starting* point for a [full sync](#full-sync).
Supports the following time format `YYYY-MM-DDTHH:MM:SSZ`

```yaml
start_time: 2022-04-01T04:44:16Z
```

#### `end_time`

A UTC timestamp the connector uses to determine which objects to extract and sync from Microsoft Teams. Determines the *stopping* point for a [full sync](#full-sync).
Supports the following time format `YYYY-MM-DDTHH:MM:SSZ`

```yaml
end_time: 2022-04-01T04:44:16Z
```

By default this is set to the current time at execution.

#### `log_level`

The level or severity that determines the threshold for [logging](#log-errors-and-exceptions) a message. One of the following values:

- `DEBUG`
- `INFO` (default)
- `WARN`
- `ERROR`

```yaml
log_level: INFO
```

By default, it is set to `INFO`.

#### `retry_count`

The number of retries to perform when there is a server error. The connector applies an exponential back-off algorithm to retries.

```yaml
retry_count: 3
```

By default, it is set to `3`.

#### `ms_teams_sync_thread_count`

The number of threads the connector will run in parallel when fetching documents from the Microsoft Teams. By default, the connector uses 5 threads.

```yaml
ms_teams_sync_thread_count: 5
```

#### `enterprise_search_sync_thread_count`

The number of threads the connector will run in parallel when indexing documents into the Enterprise Search instance. By default, the connector uses 5 threads.

```yaml
enterprise_search_sync_thread_count: 5
```

For the Linux distribution with atleast 2 GB RAM and 4 vCPUs, you can increase the thread counts if the overall CPU and RAM are under utilized i.e. below 60-70%.

#### `microsoft_teams.user_mapping`

The pathname of the CSV file containing the user identity mappings for [document-level permissions (DLP)](#use-document-level-permissions-dlp).

```yaml
microsoft_teams.user_mapping: 'C:/Users/banon/microsoft_teams_1/identity_mappings.csv'
```

#### Enterprise Search compatibility

The Microsoft Teams connector package is compatible with Elastic deployments that meet the following criteria:

- Elastic Enterprise Search version 7.13.0 or later.
- An Elastic subscription that supports this feature. Refer to the Elastic subscriptions pages for [Elastic Cloud](https://www.elastic.co/subscriptions/cloud) and [self-managed](https://www.elastic.co/subscriptions) deployments.

#### Runtime dependencies

Each Microsoft Teams connector requires a runtime environment that satisfies the following dependencies:

- Windows, MacOS, or Linux server. The connector has been tested with CentOS 7, MacOS Monterey v12.0.1, and Windows 10.
- Python version 3.6 or later.
- To extract content from images: Java version 7 or later, and [`tesseract` command](https://github.com/tesseract-ocr/tesseract) installed and added to `PATH`
- To schedule recurring syncs: a job scheduler, such as `cron`

## Connector Limitations

- If the same attachment is shared in multiple user chats in Microsoft Teams, Teams assigns the same ID for all instances of that attachment. As a result, Workplace Search permissions are indexed for any one of the user chats that contain this attachment.
