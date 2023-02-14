# Python imports
import json
import logging
import os
import sys
sys.path.insert(0, "{}/package".format(os.environ.get("LAMBDA_TASK_ROOT", sys.path[0])))

# 3rd party imports
import boto3

# local imports

# global variables
log = logging.getLogger()
dynamodb_client = boto3.client("dynamodb")
dynamodb_table = os.environ.get("DYNAMODB_TABLE", "go-vanity-urls")


def get_event_value(event, key):
  """Gets a value from the event and raises an Exception if it is missing.

  Parameters:
    event (dict):   Dictionary containing event information.
    key (str):      The event key to retrieve the value for.
  
  Returns:
    value (object): The value of the key.

  Raises:
    Exception:  If the value missing from the event.
  """
  value = event.get(key, None)
  if value is None:
    msg = "'{}' is missing from the event".format(key)
    log.fatal(msg)
    raise Exception(msg)
  return value


def lambda_handler(event, context):
  """AWS Lambda main entrypoint.
  
  Parameters:
    event (dict):   Event data that triggered the function.
    context (dict): Additional function context.
  """
  # initialize logging
  log.setLevel(logging.INFO)
  log.info("=== Starting go-vanity-server ===")
  log.info("sys.path: {}".format(sys.path))
  log.info("boto3 version: {}\n".format(boto3.__version__))

  try:
    # get request information
    headers = get_event_value(event, "headers")
    uri = get_event_value(event, "path")
    host = headers.get("Host", None)
    if host is None:
      raise Exception("'Host' header is not set")
    log.info("Vanity Host: {}".format(host))
    log.info("Vanity URI:  {}".format(uri))

    # search for requested host and path in DynamoDB
    while uri != "":
      log.info("Searching DB for URL: https://{}{}".format(host, uri))
      results = dynamodb_client.query(TableName=dynamodb_table,
                                      KeyConditionExpression="RequestHost = :host and RequestURI = :uri",
                                      ExpressionAttributeValues={
                                          ":host": {
                                              "S": host,
                                          },
                                          ":uri": {
                                              "S": uri,
                                          },
                                      })
      for item in results.get("Items", []):
        item_uri = item.get("RequestURI", {}).get("S", None)
        if item_uri is None:
          log.warn("'RequestURI' string is missing from entry - skipping")
          continue
        repo_url = item.get("RepositoryURL", {}).get("S", None)
        if repo_url is None:
          log.warn("'RepositoryURL' string is missing from entry - skipping")
        vcs = item.get("VCS", {}).get("S", "git")
        source = item.get("Source", {})
        home_url = source.get("Home", {}).get("S", repo_url)
        dir_url = source.get("Directory", {}).get("S", "{}/tree/master{{/dir}}".format(home_url))
        file_url = source.get("File", {}).get("S", "{}/blob/master{{/dir}}/{{file}}#L{{line}}".format(home_url))
        body = """
<!DOCTYPE html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="go-import" content="{}{} {} {}">
  <meta name="go-source" content="{}{} {} {} {}">
  <meta http-equiv="refresh" content="0; url=https://godoc.org/{}{}">
</head>
<body>
Nothing to see here; <a href="https://godoc.org/{}{}">see the package on godoc</a>.
</body>
</html>
""".format(host, uri, vcs, repo_url, host, uri, home_url, dir_url, file_url, host, uri, host, uri).strip()
        log.info("Found match: {}".format(repo_url))
        log.info("Response:\n{}".format(body))
        return {"statusCode": 200, "body": body}
      uri = uri[0:uri.rfind("/")]
    log.warning("Not Found")
    return {
        "statusCode": 404,
        "body": "Not Found",
    }
  except Exception as e:
    msg = "{}".format(e)
    log.fatal(e)
    return {"statusCode": 500, "body": msg}
  finally:
    log.info("=== Finished go-vanity-server ===\n")


# invocation for debugging purposes
if __name__ == "__main__":
  if len(sys.argv) == 1:
    print("USAGE: {} <JSON event file>".format(sys.argv[0]))
    sys.exit(1)
  ch = logging.StreamHandler()
  log.addHandler(ch)
  try:
    with open(sys.argv[1], "r") as event_file:
      event = json.load(event_file)
    lambda_handler(event, None)
  except Exception as e:
    log.error(e)
