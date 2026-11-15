using MessagePack;
namespace Consumer
{
    [MessagePackObject]
    public class Order { [Key(0)] public int Id { get; set; } [Key(1)] public string Name { get; set; } }

    [GeneratedMessagePackResolver]
    partial class AppResolver
    {
        // Code written by hand by the user: must stay measured by coverage.
        public static int UserBusinessRule(int x) => x > 10 ? x * 2 : x;
    }
}
