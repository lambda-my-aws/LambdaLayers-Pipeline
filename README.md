The Pipeline to create pipelines using a Layer to generate Layers
=================================================================

Why do I need a Function to Initialize the CodeCommit repository?
-----------------------------------------------------------------

WHen you create a new repository (bare) it has no commit ID yet and therefore no branch. When CloudFormation creates a new CodePipeline, the pipeline tries immediately to run a full execution, and there is no property in the CodePipeline object to disable that behaviour.
As the Source stage is to gather the code from the latest commit in the branch you indicated, here master, the first stage fails.
And for some reason, using CloudWatch even to kick off the Pipeline, when you push that first commit to the repository, even if the branch now exists, it won't kick off the template until you go and click on retry (or call the API to run the pipeline). And that just annoys me. I do not want a human to have to do anything. The build step can fail, that's fine, it will go again as soon as you do create a new commit with buildspec and other stuff you need.

Why do I use Troposphere to create a new template for every new Lambda Layer Version ?
--------------------------------------------------------------------------------------

I emphasize on the fact that you are not creating a new Lambda Layer, but a new Version of a Layer. If the layer didn't exist before, you are creating the first version of it. CloudFormation, on update, if the Code property changed to a new S3 location, which it will given the pipeline will provide a new build, CFN will update the stack. That would mean that, CFN will delete the previous version and create the new one (apparently the previous one would still be there but at least not be there in the UI ..). So with Troposphere, thanks to the fact that I use Python, every time the template is generated, I change the LogicalId of the resource. Therefore, a new Layer Version is created but because of the DeletionPolicy=Retain for the previous one, we now have both of them available.

Why use a Lambda Function to generate the new template ?
-------------------------------------------------------------

In addition to the LogicalId situation explained above, the other reason is that the cli `aws cloudformation package` which would normally replace the `Code` properties of where your new Zip file of the Lambda Function is into your source template and generate the one bespoke necessary for the Deploy step using CloudFormation, at the time of writting this, package does not support the LambdaLayer object / Resource Type.

Why not run Troposphere within the build step?
---------------------------------------------------

Using a Lambda function gives me great flexibility to share that same function across all pipelines regardless of the layer that is being built. Also, I do not want to have to either add the script into the layer source (it has no business being there). If I did, and I change the script, I would have to do it for each and every Layer repository and this is not scalable.

The chicken and Egg
===================

We have a bit of a chicken and egg situation in what this Pipeline aims to achieve:
We want to create a pipeline that creates a new Lambda Layer Version, but to achieve this, we need a Lambda function that generates CFN templates with Troposphere and the Function to exist in order for the Pipeline to be complete.

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
