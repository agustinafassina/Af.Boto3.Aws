import boto3

# Crear un cliente de EC2 para poder listar regiones
ec2 = boto3.client('ec2')

# Obtener todas las regiones
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

# Iterar sobre cada región
for region in regions:
    print(f"Checking region: {region}")
    
    # Crear un cliente EC2 para la región actual
    regional_ec2 = boto3.client('ec2', region_name=region)
    
    # Describir todas las instancias
    response = regional_ec2.describe_instances()
    
    # Lista para almacenar instancias sin el tag "Project"
    instances_without_project_tag = []

    # Recorrer las instancias
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Comprobar si existe el tag "Project"
            if 'Tags' not in instance or not any(tag['Key'] == 'Project' for tag in instance['Tags']):
                instances_without_project_tag.append(instance['InstanceId'])

    # Mostrar instancias sin el tag "Project"
    if instances_without_project_tag:
        print(f"Instances without 'Project' tag in {region}:")
        for instance_id in instances_without_project_tag:
            print(f"  - {instance_id}")
    else:
        print(f"No instances without 'Project' tag in region: {region}")