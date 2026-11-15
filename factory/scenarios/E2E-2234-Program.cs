using System;
using System.IO;
using System.Linq;
using MessagePack;
using MessagePack.Resolvers;

namespace App;

// Issue #2234, AC-2: no code is generated for a type with SuppressSourceGeneration = true.
// Control: a normal [MessagePackObject] type in the same project still gets a generated formatter.

[MessagePackObject(SuppressSourceGeneration = true)]
public class Suppressed
{
    [Key(0)] public int Id { get; set; }
    [Key(1)] public string Name { get; set; }
}

[MessagePackObject]
public partial class Control
{
    [Key(0)] public int Id { get; set; }
}

// covers: AC-2
public static class Program
{
    public static int Main()
    {
        var rt = typeof(Program).Assembly.GetType("MessagePack.GeneratedMessagePackResolver");
        Console.WriteLine($"generated resolver present: {(rt != null ? "yes" : "NO")}");
        if (rt == null) return 1;
        var inst = (IFormatterResolver)rt.GetField("Instance").GetValue(null);
        Console.WriteLine($"AC-2 generated formatter for Suppressed: {(inst.GetFormatter<Suppressed>() == null ? "none (expected)" : "PRESENT")}");
        Console.WriteLine($"control generated formatter for Control: {(inst.GetFormatter<Control>() != null ? "present (expected)" : "MISSING")}");

        var genTypes = typeof(Program).Assembly.GetTypes().Where(t => t.FullName.Contains("Formatter") && t.FullName.Contains("Suppressed")).ToArray();
        Console.WriteLine($"AC-2 generated formatter types named after Suppressed: {genTypes.Length}");

        // Generated source files on disk (EmitCompilerGeneratedFiles): search the project directory upwards.
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "App.csproj"))) dir = dir.Parent;
        var gen = dir == null ? null : Path.Combine(dir.FullName, "generated");
        if (gen != null && Directory.Exists(gen))
        {
            var files = Directory.GetFiles(gen, "*.cs", SearchOption.AllDirectories);
            Console.WriteLine($"generated source files mentioning Suppressed: {files.Count(f => File.ReadAllText(f).Contains("Suppressed"))}");
            Console.WriteLine($"control generated source files mentioning Control: {files.Count(f => File.ReadAllText(f).Contains("Control"))}");
        }
        else
        {
            Console.WriteLine("generated source directory: NOT FOUND");
        }

        var bytes = MessagePackSerializer.Serialize(new Suppressed { Id = 7, Name = "seven" }, MessagePackSerializerOptions.Standard);
        var back = MessagePackSerializer.Deserialize<Suppressed>(bytes, MessagePackSerializerOptions.Standard);
        Console.WriteLine($"Suppressed round-trip via dynamic resolver: {(back.Id == 7 && back.Name == "seven" ? "OK" : "DIFFERENT")}");
        return 0;
    }
}
