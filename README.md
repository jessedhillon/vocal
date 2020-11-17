# Notes

## Compiling OAS spec

Validate the spec with,
```
$ node node_modules/swagger-cli/swagger-cli.js validate -d openapi/openapi.yaml
```

Then compile with,
```
$ node node_modules/swagger-cli/swagger-cli.js bundle -o build/openapi.yaml openapi/openapi.yaml
```

## Running migrations

Migrate up to `head`
```
$ vocal-cli database up head
```

Migrate backward,
```
$ vocal-cli database down <revision>
```
