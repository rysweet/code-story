# Disaster Recovery Guide

This document outlines the disaster recovery (DR) procedures for the Code Story application. It covers backup strategies, restore procedures, and general guidance for ensuring business continuity in case of failures.

## Architecture Overview

The disaster recovery system consists of the following components:

1. **Primary Storage Account**: Stores regular backups of the Neo4j database and application configuration in the primary region.
2. **Secondary Storage Account**: Geo-redundant storage in a secondary region for additional resilience.
3. **Automation Account**: Handles scheduled backup jobs and monitoring.
4. **Alert System**: Notifies administrators of backup failures or other issues.

## Backup Procedures

### Automated Backups

The system performs regular automated backups:

- **Neo4j Database**: Daily backups at 2:00 AM UTC
- **Application Configuration**: Daily backups at 2:00 AM UTC
- **Retention**: Backups are retained for 30 days by default

### Manual Backups

You can also perform manual backups using the provided scripts:

```bash
# Backup Neo4j database
./infra/scripts/backup_neo4j.sh \
  --neo4j-uri bolt://your-neo4j-host:7687 \
  --neo4j-username neo4j \
  --neo4j-password your-password \
  --storage-account your-storage-account \
  --container neo4j-backups
```

## Restore Procedures

In case of failure, you can restore from backups using the following procedures:

### Listing Available Backups

```bash
# List available Neo4j backups
./infra/scripts/restore_neo4j.sh \
  --storage-account your-storage-account \
  --container neo4j-backups \
  --list-only
```

### Restoring Neo4j Database

```bash
# Restore Neo4j database
./infra/scripts/restore_neo4j.sh \
  --neo4j-uri bolt://your-neo4j-host:7687 \
  --neo4j-username neo4j \
  --neo4j-password your-password \
  --storage-account your-storage-account \
  --container neo4j-backups \
  --backup-file neo4j-backup-20230101-120000.tar.gz
```

## Disaster Recovery Testing

It's crucial to regularly test the disaster recovery procedures to ensure they work as expected.

### Recommended Testing Schedule

- **Backup Verification**: Weekly
- **Restore Test**: Monthly
- **Full DR Drill**: Quarterly

### Test Procedure

1. Create a test environment using the same infrastructure as production
2. Download the latest backup from Azure Storage
3. Perform a restore operation in the test environment
4. Verify data integrity and application functionality
5. Document and address any issues encountered

## Recovery Time and Recovery Point Objectives

- **Recovery Time Objective (RTO)**: The system is designed to be restored within 1 hour
- **Recovery Point Objective (RPO)**: Maximum data loss of 24 hours (based on daily backup schedule)

## Failure Scenarios and Response Procedures

### Database Corruption

1. Stop all services accessing the database
2. Restore the database from the most recent backup
3. Verify data integrity
4. Restart services

### Regional Outage

1. Provision new resources in the secondary region
2. Restore database and configuration from geo-redundant storage
3. Update DNS or service endpoints to point to the new resources
4. Verify system functionality

### Complete System Failure

1. Provision new infrastructure using infrastructure-as-code templates
2. Restore database and configuration from backups
3. Deploy application containers
4. Verify system functionality
5. Update DNS or service endpoints to point to the new system

## Contact Information

In case of emergencies, contact:

- Primary: disaster-recovery@example.com
- Secondary: on-call-support@example.com
- Emergency Hotline: +1-555-123-4567

## Additional Resources

- [Azure Storage Redundancy Documentation](https://docs.microsoft.com/en-us/azure/storage/common/storage-redundancy)
- [Neo4j Backup and Restore Documentation](https://neo4j.com/docs/operations-manual/current/backup-restore/)
- [Azure Automation Documentation](https://docs.microsoft.com/en-us/azure/automation/)