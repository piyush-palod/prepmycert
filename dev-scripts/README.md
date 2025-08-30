# Development Scripts Directory

⚠️ **IMPORTANT: DELETE THIS ENTIRE FOLDER BEFORE PRODUCTION DEPLOYMENT** ⚠️

This directory contains temporary development utilities that should NOT be deployed to production.

## Available Scripts

### `set_exclusive_admin.py`
**Purpose**: Make `zeus0091@gmail.com` the ONLY admin user in the system

**What it does**:
1. Removes admin privileges from ALL existing users
2. Finds the user with `zeus0091@gmail.com` 
3. Promotes ONLY that user to admin status
4. Provides detailed logging and verification

**Usage**:
```bash
# Show current admin users
python dev-scripts/set_exclusive_admin.py --show

# Run the exclusive admin setup
python dev-scripts/set_exclusive_admin.py
```

**Safety Features**:
- Requires explicit confirmation (`YES`)
- Shows before/after state
- Detailed logging of all changes
- Hardcoded target email prevents accidents
- Error handling with rollback

## Security Notes

- These scripts are for development setup only
- They bypass normal user registration flows
- They modify admin privileges directly in database
- **NEVER** deploy to production servers

## Cleanup Instructions

Before deploying to production:

1. **Test thoroughly** - Ensure admin access works correctly
2. **Verify functionality** - Test all admin features  
3. **Delete folder** - Remove entire `dev-scripts/` directory
4. **Clean commit** - Don't commit dev scripts to production branch

```bash
# Remove dev scripts before production
rm -rf dev-scripts/
```

---

🔒 **Remember**: These are powerful administrative tools. Use with caution!