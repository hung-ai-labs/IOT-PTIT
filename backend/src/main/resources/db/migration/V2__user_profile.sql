ALTER TABLE users ADD COLUMN IF NOT EXISTS student_id VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS school VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS contact_email VARCHAR(150);
UPDATE users SET
    student_id = COALESCE(student_id, 'B23DCCN361'),
    school = COALESCE(school, 'Học Viện Công Nghệ Bưu Chính Viễn Thông'),
    contact_email = COALESCE(contact_email, 'Hungmk2005@gmail.com')
WHERE email = 'admin@ptit.edu.vn' AND full_name = 'Nguyễn Xuân Hùng';
