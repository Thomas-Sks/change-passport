using System.Reflection;
using System.Runtime.Loader;
// Probe a consumer build: for each target, which types end up excluded from code coverage,
// and is hand-written user code (methods declared in the source, not generated) still measured?
static bool Excl(Type t) => t.GetCustomAttributesData().Any(a => a.AttributeType.Name == "ExcludeFromCodeCoverageAttribute")
    || (t.DeclaringType != null && Excl(t.DeclaringType));
foreach (var tf in new[] { "net8.0", "netstandard2.0" })
{
    var dir = Path.GetFullPath(Path.Combine(args[0], tf));
    if (!File.Exists(Path.Combine(dir, "Consumer.dll"))) continue;
    var ctx = new AssemblyLoadContext(tf, true);
    ctx.Resolving += (c, n) => { var p = Path.Combine(dir, n.Name + ".dll"); return File.Exists(p) ? c.LoadFromAssemblyPath(p) : null; };
    var asm = ctx.LoadFromAssemblyPath(Path.Combine(dir, "Consumer.dll"));
    Console.WriteLine($"== consumer {tf}");
    var types = asm.GetTypes().Where(t => t.Namespace == "Consumer" && !t.Name.StartsWith("<")).OrderBy(t => t.FullName).ToList();
    foreach (var t in types) Console.WriteLine($"  {(Excl(t) ? "EXCLUDED" : "measured")}  {t.FullName}");
    foreach (var t in types)
        foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.DeclaredOnly).Where(m => m.Name.StartsWith("User")))
            Console.WriteLine($"  -> user code {t.Name}.{m.Name}: {(Excl(t) ? "EXCLUDED from coverage" : "measured")}");
}
