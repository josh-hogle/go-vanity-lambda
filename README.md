# Go Vanity Server

This tool consists of a Lambda function, an API Gateway and a DynamoDB table which work together to serve as a vanity URL server for Golang projects.

Typically Go imports must refer to a full repository path to the import such as `github.com/sirupsen/logrus`.  This makes moving repository locations difficult as all code which refers to those locations has to be updated.  Instead, a Go vanity URL can be used to redirect requests to any location possible.  For example, `go.joshhogle.com/logger` could really point to `github.com/sirupsen/logrus`.

There are many implementations on the Internet of Go vanity servers but this implementation requires no servers.  It uses AWS serverless technologies to accomplish this goal.

This document covers how to set up this package to run as your own Go vanity server.

## 1. Create an IAM role

The first step is to create an IAM role for the Lambda function so it can access various resources in the AWS account.  The `iam/roles` folder contains JSON files for the role that is required.  The basic role gives a great deal of permissions to the function while the **restricted** version limits those permissions greatly.  Either document can be used to create a cusom policy that is attached to the role or used as an inline policy directly on the role.

## 2. Create the Lambda function

The core functionality for the vanity server comes from this Lambda function.  You will need to create a new Lambda function called **go-vanity-server** using **Python 3.7** and assign the role you created in step 1 to this function.  After authenticating using the AWS CLI, use the `upload-function.sh go-vanity-server` command to upload the function to Lambda.

You may wish to also tweak the timeout for the function to something beyond 3 seconds.  15 seconds should be a good default, but it will depend on the number of vanity URLs you are serving.

**NOTE**: You do not have to name the function **go-vanity-server** but if you decide to alter the name, please be sure to change all references elsewhere to match the name of your function.

## 3. Create a CloudWatch log group (optional)

The Lambda function will log output while processing a request.  If you wish to see this content and are using the **restricted** version of the IAM policy, you will need to open CloudWatch and create a new log group called **/aws/lambda/go-vanity-server**.  You'll probably want to adjust its events to expire after 1 day unless you want to store quite a bit of data.  Again, this will depend on the number of requests to your vanity server.

## 4. Create a DynamoDB table

DynamoDB holds the configuration for what vanity URLs will be served and how those URLs map to the actual repository locations.  Create a new table called **go-vanity-urls** with the **Primary key** set to **RequestHost** which is a **String** and add a sort key called **RequestURI** which is also a **String**.  The remaining settings you can adjust to your liking.

**NOTE**: You can change the name of this table to whatever you'd like.  However, if you choose to do so, you will need to define the **DYNAMODB_TABLE** environment variable on your Lambda function to match the new table name.

## 5. Create a certificate in ACM

In order to serve your vanity URLs, you will need to create SSL certificates using Amazon Certificate Manager.  These certificates will be attached to your API gateway to host your custom domain.  Be sure to create the certificate in the same region as your API Gateway.

## 6. Create an API Gateway

The final step in the setup is to create a new API using the Amazon API Gateway service.  You can name your API anything you'd like but be sure to create a **REST** API.  Set the **Endpoint Type** to **Regional**.

Once your API has been created, create a new resource called **{proxy+}** and set the path to the same value.  Click the **ANY** method that is created and delete it.  Add a new **GET** method instead.

Select **Lambda Function Proxy** for the **Integration type** and enter **go-vanity-server** for the **Lambda Function** name and save the settings.

Click the **Method Response** and remove the **application/json** response under the **200** status code response body.  Add a new **text/html** response body using the **Empty** model.

## 7. Deploy your API

Once the other steps have been completed, it's time to deploy the API.  Simply choose the **Deploy API** action and configure a stage.

After the deploy is completed, it's time to expose your vanity server using your custom domain.  Go to **Custom Domain Names** and create a new custom domain name attached to the ACM certificate you previously created.  After creating the domain name, edit the **Base Path Mappings** to add the **/** path to your API and stage that was just created.

Test your API by making a `curl` request to the new domain.  You should receive a `Not Found` response.

## Adding Vanity URLs

Now that the vanity server has been set up and configured, the final step is to actually start serving content.  This is accomplished by adding entries to the **go-vanity-urls** table in DynamoDB.

Each item created in the table must use the following format:

```json
{
  "RequestHost": {
    "S": "your.custom.domain",
  },
  "RequestURI": {
    "S": "/vanity/URI"
  },
  "RepositoryURL": {
    "S": "https://the.actual.location/of/the/go/repository"
  },
  "VCS": {
    "S": "git"
  },
  "Source": {
    "M": {
      "Home": {
        "S": "https://the.actual.location/of/the/go/repository"
      },
      "Directory": {
        "S": "https://the.actual.location/of/the/go/repository/tree/master{/dir}"
      },
      "File": {
        "S": "https://the.actual.location/of/the/go/repository/blob/master{/dir}/{file}#L{line}"
      }
    }
  }
}
```

| **Field Name** | **Type** | **Description** |
|------------|------|-------------|
| RequestHost | String | The **Host** header from the request, which should be the vanity domain |
| RequestURI  | String | The URI from the request; must start with a `/` |
| RepositoryURL | String | The actual full path to the code repository |
| VCS | String | (Optional) The type of version control system for the repository; defaults to **git** |
| Source | Map | (Optional) Settings to return in the **go-source** meta tag |
| Source.Home | String | (Optional) Usually identical to the `RepositoryURL` field; defaults to same vaule for `RepositoryURL` |
| Source.Directory | String | (Optional) URL to reach a specific directory within the source; defaults to `RepositoryURL/tree/master{/dir}` |
| Source.File | String | (Optional) URL to reach a specific file and line within the source; defaults to `RepositoryURL/tree/master{/dir}/{file}#L{line}` |

For additional information on how HTML meta tags are used by Golang, please see the following links:

- <https://golang.org/cmd/go/>
- <https://github.com/golang/gddo/wiki/Source-Code-Links>

Once you have added an item to the database, you can test it by issuing a `curl` command using the `https://{RequestHost}{RequestURI}` format.  For example:

`curl -s https://go.joshhogle.com/apps/jeeves`

You should see the HTML document that would be returned to Go commands such as `go get`.

## Debugging and Logging

By default, all output from the function is sent to CloudWatch Logs and placed into the **/aws/lambda/go-vanity-server** Log Group.

The function can be invoked from Lambda by executing the function with a sample event or it can be run from the command-line directly.  When running directly from the command-line, the function will log to stdout instead of CloudWatch.

The `lambda/functions/go-vanity-server/test-event.json` file contains a sample test event that you can use.

## Additional Help or Questions

If you have questions about this project, find a bug or wish to submit a feature request, please [submit an issue](https://github.com/josh-hogle/go-vanity-server/issues).
