def extract_vnet_from_subnet(subnet_id):
    return subnet_id.split("/subnets/")[0]

def get_name_from_id(resource_id):
    return resource_id.split("/")[-1]