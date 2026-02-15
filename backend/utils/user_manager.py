#!/usr/bin/env python3
"""
User Management GUI Tool for Electrician Work Log System
A simple Tkinter application to manage users in the database
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os


class UserManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Electrician Work Log - User Manager")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Database path - updated to use backend database location
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        self.db_path = os.path.join(backend_dir, 'database.db')

        # Initialize UI
        self.setup_ui()
        self.refresh_users()

    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="User Management",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.N), padx=(0, 10))

        # Buttons
        ttk.Button(buttons_frame, text="Add User",
                   command=self.add_user_dialog).grid(row=0, column=0, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Edit User",
                   command=self.edit_user_dialog).grid(row=1, column=0, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Delete User",
                   command=self.delete_user).grid(row=2, column=0, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Reset Password",
                   command=self.reset_password_dialog).grid(row=3, column=0, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Toggle Active",
                   command=self.toggle_active).grid(row=4, column=0, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Refresh",
                   command=self.refresh_users).grid(row=5, column=0, pady=5, sticky=tk.W)

        # Users table frame
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=1, column=1, columnspan=2,
                         sticky=(tk.W, tk.E, tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Treeview for users
        columns = ('ID', 'Username', 'Full Name', 'Role',
                   'Active', 'Created', 'Last Login')
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show='headings', height=15)

        # Define headings
        self.tree.heading('ID', text='ID')
        self.tree.heading('Username', text='Username')
        self.tree.heading('Full Name', text='Full Name')
        self.tree.heading('Role', text='Role')
        self.tree.heading('Active', text='Active')
        self.tree.heading('Created', text='Created')
        self.tree.heading('Last Login', text='Last Login')

        # Configure column widths
        self.tree.column('ID', width=50)
        self.tree.column('Username', width=100)
        self.tree.column('Full Name', width=150)
        self.tree.column('Role', width=80)
        self.tree.column('Active', width=60)
        self.tree.column('Created', width=100)
        self.tree.column('Last Login', width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Grid the treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=2, column=0, columnspan=3,
                        sticky=(tk.W, tk.E), pady=(10, 0))

    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def refresh_users(self):
        """Refresh the users list"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Get users from database
            conn = self.get_db_connection()
            users = conn.execute('''
                SELECT id, username, full_name, role, is_active, created_at, last_login
                FROM users ORDER BY created_at DESC
            ''').fetchall()
            conn.close()

            # Populate treeview
            for user in users:
                created = user['created_at'][:10] if user['created_at'] else 'N/A'
                last_login = user['last_login'][:10] if user['last_login'] else 'Never'
                active = 'Yes' if user['is_active'] else 'No'

                self.tree.insert('', tk.END, values=(
                    user['id'],
                    user['username'],
                    user['full_name'],
                    user['role'],
                    active,
                    created,
                    last_login
                ))

            self.status_var.set(f"Loaded {len(users)} users")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {str(e)}")

    def get_selected_user(self):
        """Get the selected user from the treeview"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user first")
            return None

        item = self.tree.item(selection[0])
        return {
            'id': item['values'][0],
            'username': item['values'][1],
            'full_name': item['values'][2],
            'role': item['values'][3],
            'is_active': item['values'][4] == 'Yes'
        }

    def hash_password(self, password):
        """Hash a password using werkzeug (same as auth_service)"""
        return generate_password_hash(password)

    def add_user_dialog(self):
        """Show dialog to add a new user"""
        dialog = UserDialog(self.root, "Add User")
        if dialog.result:
            try:
                conn = self.get_db_connection()

                # Check if username already exists
                existing = conn.execute(
                    'SELECT id FROM users WHERE username = ?',
                    (dialog.result['username'],)
                ).fetchone()

                if existing:
                    messagebox.showerror("Error", "Username already exists")
                    conn.close()
                    return

                # Hash password and insert user
                password_hash = self.hash_password(dialog.result['password'])

                conn.execute('''
                    INSERT INTO users (username, password_hash, full_name, role, is_active)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    dialog.result['username'],
                    password_hash,
                    dialog.result['full_name'],
                    dialog.result['role'],
                    1  # Active by default
                ))

                conn.commit()
                conn.close()

                self.refresh_users()
                self.status_var.set(
                    f"User '{dialog.result['username']}' added successfully")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to add user: {str(e)}")

    def edit_user_dialog(self):
        """Show dialog to edit selected user"""
        user = self.get_selected_user()
        if not user:
            return

        dialog = UserDialog(self.root, "Edit User", user)
        if dialog.result:
            try:
                conn = self.get_db_connection()

                # Check if new username conflicts with existing users (excluding current user)
                if dialog.result['username'] != user['username']:
                    existing = conn.execute(
                        'SELECT id FROM users WHERE username = ? AND id != ?',
                        (dialog.result['username'], user['id'])
                    ).fetchone()

                    if existing:
                        messagebox.showerror(
                            "Error", "Username already exists")
                        conn.close()
                        return

                # Update user (without password change)
                conn.execute('''
                    UPDATE users 
                    SET username = ?, full_name = ?, role = ?
                    WHERE id = ?
                ''', (
                    dialog.result['username'],
                    dialog.result['full_name'],
                    dialog.result['role'],
                    user['id']
                ))

                conn.commit()
                conn.close()

                self.refresh_users()
                self.status_var.set(
                    f"User '{dialog.result['username']}' updated successfully")

            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to update user: {str(e)}")

    def delete_user(self):
        """Delete selected user"""
        user = self.get_selected_user()
        if not user:
            return

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete user '{user['username']}'?\n\nThis action cannot be undone."):
            return

        try:
            conn = self.get_db_connection()
            conn.execute('DELETE FROM users WHERE id = ?', (user['id'],))
            conn.commit()
            conn.close()

            self.refresh_users()
            self.status_var.set(
                f"User '{user['username']}' deleted successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete user: {str(e)}")

    def reset_password_dialog(self):
        """Reset password for selected user"""
        user = self.get_selected_user()
        if not user:
            return

        # Get new password
        password = simpledialog.askstring("Reset Password",
                                          f"Enter new password for '{user['username']}':",
                                          show='*')
        if not password:
            return

        if len(password) < 4:
            messagebox.showerror(
                "Error", "Password must be at least 4 characters long")
            return

        try:
            conn = self.get_db_connection()
            password_hash = self.hash_password(password)

            conn.execute('''
                UPDATE users SET password_hash = ? WHERE id = ?
            ''', (password_hash, user['id']))

            conn.commit()
            conn.close()

            self.status_var.set(
                f"Password reset for user '{user['username']}'")
            messagebox.showinfo("Success", "Password reset successfully")

        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to reset password: {str(e)}")

    def toggle_active(self):
        """Toggle active status for selected user"""
        user = self.get_selected_user()
        if not user:
            return

        try:
            conn = self.get_db_connection()
            new_status = 0 if user['is_active'] else 1

            conn.execute('''
                UPDATE users SET is_active = ? WHERE id = ?
            ''', (new_status, user['id']))

            conn.commit()
            conn.close()

            status_text = "activated" if new_status else "deactivated"
            self.refresh_users()
            self.status_var.set(f"User '{user['username']}' {status_text}")

        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to toggle user status: {str(e)}")


class UserDialog:
    def __init__(self, parent, title, user_data=None):
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

        # Variables
        self.username_var = tk.StringVar(
            value=user_data['username'] if user_data else '')
        self.full_name_var = tk.StringVar(
            value=user_data['full_name'] if user_data else '')
        self.role_var = tk.StringVar(
            value=user_data['role'] if user_data else 'worker')
        self.password_var = tk.StringVar()

        self.is_edit = user_data is not None

        self.setup_dialog()

        # Wait for dialog to close
        self.dialog.wait_window()

    def setup_dialog(self):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Username
        ttk.Label(main_frame, text="Username:").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.username_var, width=30).grid(
            row=0, column=1, pady=5, padx=(10, 0))

        # Full Name
        ttk.Label(main_frame, text="Full Name:").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.full_name_var, width=30).grid(
            row=1, column=1, pady=5, padx=(10, 0))

        # Role
        ttk.Label(main_frame, text="Role:").grid(
            row=2, column=0, sticky=tk.W, pady=5)
        role_combo = ttk.Combobox(main_frame, textvariable=self.role_var, width=27,
                                  values=['admin', 'supervisor', 'worker'], state='readonly')
        role_combo.grid(row=2, column=1, pady=5, padx=(10, 0))

        # Password (only for new users)
        if not self.is_edit:
            ttk.Label(main_frame, text="Password:").grid(
                row=3, column=0, sticky=tk.W, pady=5)
            ttk.Entry(main_frame, textvariable=self.password_var, width=30,
                      show='*').grid(row=3, column=1, pady=5, padx=(10, 0))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Save", command=self.save).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel",
                   command=self.cancel).pack(side=tk.LEFT, padx=5)

    def save(self):
        """Save user data"""
        username = self.username_var.get().strip()
        full_name = self.full_name_var.get().strip()
        role = self.role_var.get()
        password = self.password_var.get()

        # Validation
        if not username:
            messagebox.showerror("Error", "Username is required")
            return

        if not full_name:
            messagebox.showerror("Error", "Full name is required")
            return

        if not self.is_edit and not password:
            messagebox.showerror("Error", "Password is required")
            return

        if not self.is_edit and len(password) < 4:
            messagebox.showerror(
                "Error", "Password must be at least 4 characters long")
            return

        # Save result
        self.result = {
            'username': username,
            'full_name': full_name,
            'role': role,
            'password': password
        }

        self.dialog.destroy()

    def cancel(self):
        """Cancel dialog"""
        self.dialog.destroy()


def main():
    """Main function"""
    # Check if database exists - updated path
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(backend_dir, 'database.db')

    if not os.path.exists(db_path):
        # Create helpful error message with correct path
        messagebox.showerror(
            "Error",
            f"Database not found at:\n{db_path}\n\n" +
            "Please run the main Flask application first to create the database.\n\n" +
            "Run: python backend/run.py"
        )
        return

    print(f"✅ Database found at: {db_path}")

    # Create and run the application
    root = tk.Tk()
    app = UserManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
