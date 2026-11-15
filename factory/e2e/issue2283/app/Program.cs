using System;
using MessagePack;
using MessagePack.Resolvers;
using Lib;

namespace App;

// Verbatim from issue #2283, plus a runtime check written from AC-2 and AC-3.
[MessagePackObject]
public sealed partial record Cmd([property: Key(0)] string Scope)
{
    [Key(1)] public Item<int> Member { get; init; }
}

public static class Program
{
    public static int Main()
    {
        var rt = typeof(Cmd).Assembly.GetType("MessagePack.GeneratedMessagePackResolver");
        Console.WriteLine($"AC-2 resolver generated in app: {(rt != null ? "yes" : "NO")}");
        if (rt == null) return 1;
        var inst = (IFormatterResolver)rt.GetField("Instance").GetValue(null);
        Console.WriteLine($"AC-2 formatter for Cmd: {(inst.GetFormatter<Cmd>() != null ? "yes" : "NO")}");
        try
        {
            var opts = MessagePackSerializerOptions.Standard.WithResolver(CompositeResolver.Create(inst, StandardResolver.Instance));
            var bytes = MessagePackSerializer.Serialize(new Cmd("scope") { Member = new Item<int>("k") }, opts);
            var back = MessagePackSerializer.Deserialize<Cmd>(bytes, opts);
            Console.WriteLine($"AC-3 round-trip: {(back.Scope == "scope" && back.Member.Key == "k" ? "OK" : "DIFFERENT")}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"AC-3 round-trip: EXCEPTION {ex.GetType().Name}");
        }
        return 0;
    }
}
