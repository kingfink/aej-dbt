select email_id, source, source_email_id, subject, sent_ts
from {{ ref("int_email_messages") }}
