select
    c.email_campaign_id,
    c.source,
    c.campaign_name,
    c.subject,
    c.campaign_date,
    c.first_sent_ts,
    c.message_count as n_messages,
    c.is_test,
    b.html as html_body,
    b.text as text_body
from {{ ref("int_email_campaigns") }} as c
left join {{ ref("stg_resend__broadcasts") }} as b on c.broadcast_id = b.broadcast_id
