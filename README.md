The Pipeline to create pipelines using a Layer to generate Layers
=================================================================

We have a bit of a chicken and egg situation in what this Pipeline aims to achieve:
We want to create a pipeline that creates new Lambda Layers, but to achieve this, we need a Lambda function that generates CFN templates with Troposphere and the Function to exist in order for the Pipeline to be complete.

So initially we need to operate in an orderly fashion.

- Create the roles stack
- Create the zip file for your layer from your local environment, using the same method as in your buildspec.yml
- Generate the template from CLI using `python lambda_layer_version_pipeline_template_generator.py`
- Create the stack to create your first lambda layer
- Bundle the lambda function / script you used in step one and upload it to s3
- Generate the template to create the lambda function
- Create the stack to create the lambda function that uses the layer generated in step 2
- Create the pipeline
- Clone repository
- Add buildspec.yml and your requirements.txt file
- Enjoy the ride

