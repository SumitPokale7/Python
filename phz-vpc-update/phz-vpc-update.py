from lib import PHZAssociation

dns_hub_account = '<DNS_HUB_ACCOUNT_ID>'
dns_hub_new_vpc_id = '<DNS_HUB_NEW_VPC_ID>'
dns_hub_new_vpc_region = '<DNS_HUB_NEW_VPC_REGION>'
dns_hub_vpc_ireland = '<DNS_HUB_VPC_IRELAND>'

phzassociation = PHZAssociation(dns_hub_account)
phz_list = phzassociation._list_hosted_zones(dns_hub_vpc_ireland)

for phz in phz_list:
    try:
        phzassociation = PHZAssociation(dns_hub_account, account=phz["Owner"]["OwningAccount"])
        vpc_ids = phzassociation._get_associated_vpc_list(phz["HostedZoneId"])
        phzassociation._apply_phz_dns_hub_association(phz["HostedZoneId"], vpc_ids, dns_hub_new_vpc_id, dns_hub_new_vpc_region)
    except Exception as e:
        f = open('%s-log.txt' % phz["HostedZoneId"], 'w')
        f.write('PHZ Failed to associate with the VPC - %s' % e)
        f.close()
        print(f"Failed to associate {phz['HostedZoneId']} PHZ owned by {phz['Owner']['OwningAccount']} account with a {dns_hub_new_vpc_region} DNS Hub VPC.")
        pass
