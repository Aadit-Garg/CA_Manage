import re

file_path = 'app/admin/routes.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for log_user_action(..., {'key': value})
# e.g. log_user_action(logger, current_user, 'create_employee', {'employee_email': employee.email})

replacements = [
    (r"log_user_action\(logger, current_user, 'create_admin', \{'admin_email': user\.email\}\)",
     r"log_user_action(logger, current_user, 'create_admin', module='admin', description=f'Created admin {user.email}')"),
     
    (r"log_user_action\(logger, current_user, 'create_employee', \{'employee_email': employee\.email\}\)",
     r"log_user_action(logger, current_user, 'create_employee', module='employees', entity_type='Employee', entity_id=employee.id, description=f'Created employee {employee.email}')"),
     
    (r"log_user_action\(logger, current_user, 'edit_employee', \{'employee_email': employee\.email\}\)",
     r"log_user_action(logger, current_user, 'edit_employee', module='employees', entity_type='Employee', entity_id=employee.id, description=f'Edited employee {employee.email}')"),
     
    (r"log_user_action\(logger, current_user, action, \{'employee_email': employee\.email\}\)",
     r"log_user_action(logger, current_user, action, module='employees', entity_type='Employee', entity_id=employee.id, description=f'{action} on employee {employee.email}')"),
     
    (r"log_user_action\(logger, current_user, 'reset_employee_password', \{'employee_email': employee\.email\}\)",
     r"log_user_action(logger, current_user, 'reset_employee_password', module='employees', entity_type='Employee', entity_id=employee.id, description=f'Reset password for employee {employee.email}')"),
     
    (r"log_user_action\(logger, current_user, 'create_client', \{'client_email': profile\.email\}\)",
     r"log_user_action(logger, current_user, 'create_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Created client {profile.email}')"),
     
    (r"log_user_action\(logger, current_user, 'edit_client', \{'client_email': profile\.email\}\)",
     r"log_user_action(logger, current_user, 'edit_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Edited client {profile.email}')"),
     
    (r"log_user_action\(logger, current_user, action, \{'client_email': profile\.email\}\)",
     r"log_user_action(logger, current_user, action, module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'{action} on client {profile.email}')"),
     
    (r"log_user_action\(logger, current_user, 'disable_client', \{'client_email': profile\.email\}\)",
     r"log_user_action(logger, current_user, 'disable_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Disabled client {profile.email}')"),
     
    (r"log_user_action\(logger, current_user, 'restore_client', \{'client_email': profile\.email\}\)",
     r"log_user_action(logger, current_user, 'restore_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Restored client {profile.email}')"),
     
    (r"log_user_action\(logger, current_user, 'reset_client_password', \{'client_email': profile\.email\}\)",
     r"log_user_action(logger, current_user, 'reset_client_password', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Reset password for client {profile.email}')"),
     
    (r"log_user_action\(logger, current_user, 'bulk_import_clients', \{'count': success_count\}\)",
     r"log_user_action(logger, current_user, 'bulk_import_clients', module='clients', description=f'Bulk imported {success_count} clients')"),
     
    (r"log_user_action\(current_app\.logger, current_user, 'create_document', \{'title': doc\.title\}\)",
     r"log_user_action(current_app.logger, current_user, 'create_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Uploaded document {doc.title}')"),
     
    (r"log_user_action\(logger, current_user, 'edit_document', \{'title': doc\.title\}\)",
     r"log_user_action(logger, current_user, 'edit_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Edited document {doc.title}')"),
     
    (r"log_user_action\(logger, current_user, 'replace_document', \{'title': doc\.title\}\)",
     r"log_user_action(logger, current_user, 'replace_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Replaced document {doc.title}')"),
     
    (r"log_user_action\(logger, current_user, 'delete_document', \{'title': doc\.title\}\)",
     r"log_user_action(logger, current_user, 'delete_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Deleted document {doc.title}')"),
     
    (r"log_user_action\(logger, current_user, 'restore_document_version', \{'title': doc\.title, 'restored_version': ver\.version_number\}\)",
     r"log_user_action(logger, current_user, 'restore_document_version', module='documents', entity_type='Document', entity_id=doc.id, description=f'Restored document {doc.title} to version {ver.version_number}')"),
     
    (r"log_user_action\(logger, current_user, f'approve_\{req\.request_type\.lower\(\)\}', \{'request_id': req\.id\}\)",
     r"log_user_action(logger, current_user, f'approve_{req.request_type.lower()}', module='approvals', entity_type='ApprovalRequest', entity_id=req.id, description=f'Approved request {req.id}')"),
     
    (r"log_user_action\(logger, current_user, f'reject_\{req\.request_type\.lower\(\)\}', \{'request_id': req\.id, 'reason': reason\}\)",
     r"log_user_action(logger, current_user, f'reject_{req.request_type.lower()}', module='approvals', entity_type='ApprovalRequest', entity_id=req.id, description=f'Rejected request {req.id} for {reason}')")
]

for pat, rep in replacements:
    content = re.sub(pat, rep, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated app/admin/routes.py')
