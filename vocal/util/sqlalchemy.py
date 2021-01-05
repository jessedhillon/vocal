from alembic.operations import Operations, MigrateOperation


@Operations.register_operation('create_extension')
class CreateExtensionOp(MigrateOperation):
    def __init__(self, extension_name, checkfirst=False, schema=None, version=None):
        self.extension_name = extension_name
        self.checkfirst = checkfirst
        self.schema = schema
        self.version = version

    @classmethod
    def create_extension(cls, operations, extension_name, **kw):
        op = CreateExtensionOp(extension_name, **kw)
        return operations.invoke(op)

    def reverse(self):
        return DropExtensionOp(self. extension_name, cascade=False,
                               checkfirst=self.checkfirst, schema=self.schema,
                               version=self.version)


@Operations.implementation_for(CreateExtensionOp)
def create_extension(operations, op):
    checkfirst = "IF NOT EXISTS " if op.checkfirst else ""
    stmt = 'CREATE EXTENSION {}"{}"'.format(checkfirst, op.extension_name)

    if op.schema or op.version:
        w = []
        if op.schema:
            w.append("SCHEMA {}".format(op.schema))
        if op.version:
            w.append("VERSION '{}'".format(op.version))
        stmt += (" WITH " + " ".join(w))
    operations.execute(stmt)


@Operations.register_operation('drop_extension')
class DropExtensionOp(MigrateOperation):
    def __init__(self, extension_name, cascade, checkfirst=False):
        self.extension_name = extension_name
        self.checkfirst = checkfirst
        self.cascade = cascade

    @classmethod
    def drop_extension(cls, operations, extension_name, cascade=False, **kw):
        op = DropExtensionOp(extension_name, cascade, **kw)
        return operations.invoke(op)

    def reverse(self):
        return CreateExtensionOp(self. extension_name, checkfirst=self.checkfirst)


@Operations.implementation_for(DropExtensionOp)
def drop_extension(operations, op):
    stmt = f'DROP EXTENSION "{op.extension_name}"'
    if op.cascade:
        operations.execute(stmt + " CASCADE")
    operations.execute(stmt)
