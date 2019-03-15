The Pipeline to create pipelines using a Layer to generate Layers
=================================================================

We have a bit of a chicken and egg situation in what this Pipeline aims to achieve:
We want to create a pipeline that creates new Lambda Layers, but to achieve this, we need a Lambda function that generates CFN templates with Troposphere and the Function to exist in order for the Pipeline to be complete.

So initially we need to operate in an orderly fashion.

I added script to create the stack because I got bored of creating the file, and runnig the awscli to create the stacks.

- Create the roles stack
```bash

python lambda_layer_pipeline_roles.py --yaml --create-stack

```
- Create the zip containing the git function with
```bash

./build_function.sh codecommit_repo_initializer.py
aws s3 cp s3://some-bucket/some/key/prefix/git_init.zip

```

- Create the stack to create the Lambda function
```bash

python codecommit_init_function.py  --yaml --create-stack  --s3-bucket some-bucket --s3-key some/key/prefix/git_init.zip

```

- Create the zip file for your layer from your local environment, using the same method as in your buildspec.yml
```bash

./build_layer.sh
aws s3 cp layer.zip s3://some-bucket/some/key/prefix/layer.zip

```
- Create the stack to create the troposphere layer
```

python lambda_layer_version_pipeline_template_generator.py --yaml --create-stack --create-ssm --s3-bucket some-bucket --s3-key some/key/prefix/layer.zip --layer-name troposphere

```

- Create the pipeline template generator function

```bash

./build_function.sh lambda_layer_pipeline_generator_function.py
aws s3 cp function.zip s3://some-bucket/some/prefix/key/generator.zip
python lambda_layer_pipeline_generator_function.py --yaml  --create-stack  --s3-bucket some-bucke --s3-key some/prefix/key/generator.zip

```


NOTE - creating the SSM value is important to allow the other stacks to identify the layer ARN / Name. Using SSM instead of exports, but feel free to use what matches most your use-case.

At this point you should have
- Lambda function for the git init
- Lambda function for the template generator for pipeline
- Pipeline roles
- The Troposphere layer

Congratulations, last step:

```bash

python lambda_layer_pipeline.py --yaml --layer-name troposphere --create-stack

```

That's it, once the stack is crated, you closed the loop (chicken, eggs, I know ..) and you can simply create as many pipeline stacks as you want for each layers you will want to create and use across your accounts (note that layers are shareable across accounts).
