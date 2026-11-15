using System;
using MessagePack;

namespace Diag;

// Issue #2234: "The analyzer does not work if SuppressSourceGeneration = true".
// Each type below opts out of source generation AND breaks the MessagePack contract,
// so the analyzer must still report the diagnostic named in the comment (AC-1).

// Expected: MsgPack004 (member without [Key] / [IgnoreMember]).
[MessagePackObject(SuppressSourceGeneration = true)]
public class MissingKey
{
    [Key(0)] public int Id { get; set; }
    public string NoKey { get; set; }
}

// Expected: MsgPack005 (keys must be unique).
[MessagePackObject(SuppressSourceGeneration = true)]
public class DuplicateIntKey
{
    [Key(0)] public int A { get; set; }
    [Key(0)] public int B { get; set; }
}

// Expected: MsgPack005 (do not mix int and string keys).
[MessagePackObject(SuppressSourceGeneration = true)]
public class MixedKeys
{
    [Key(0)] public int A { get; set; }
    [Key("b")] public int B { get; set; }
}

// Expected: MsgPack005 on B AND MsgPack004 on C (a broken key must not stop the analysis of later members).
[MessagePackObject(SuppressSourceGeneration = true)]
public class DuplicateThenMissingKey
{
    [Key(0)] public int A { get; set; }
    [Key(0)] public int B { get; set; }
    public int C { get; set; }
}

// Expected: MsgPack005 on B AND MsgPack004 on C.
[MessagePackObject(SuppressSourceGeneration = true)]
public class MixedThenMissingKey
{
    [Key(0)] public int A { get; set; }
    [Key("b")] public int B { get; set; }
    public int C { get; set; }
}

// Expected: MsgPack003 (member type is not serializable).
public class NotSerializable { }

[MessagePackObject(SuppressSourceGeneration = true)]
public class BadMemberType
{
    [Key(0)] public NotSerializable Member { get; set; }
}

// covers: AC-1
public static class Program
{
    public static int Main()
    {
        Console.WriteLine("compiled; see the analyzer diagnostics listed above");
        return 0;
    }
}
